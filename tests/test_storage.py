from dataclasses import replace
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from data_model import State, ValidationError
from operations import RestockSession, PreviewError
from storage import JsonStore, StorageError, StorageConflict, SAMPLE_PATH
from test_operations import sample_state


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path=Path(self.temp.name)/'state.json'
        self.store=JsonStore(self.path)

    def start(self, state=None):
        self.store.initialize(state or sample_state())
        return RestockSession.open(self.store)

    def test_initialize_load_and_no_silent_overwrite(self):
        with self.assertRaises(StorageError): self.store.load()
        session=self.start()
        saved=self.path.read_bytes()
        with self.assertRaises(StorageError): self.store.initialize(sample_state())
        self.assertEqual(self.path.read_bytes(),saved)
        self.assertEqual(session.state,sample_state())
        self.assertEqual(list(self.path.parent.glob('*.tmp')),[])

    def test_partial_reopen_and_replenish(self):
        session=self.start(sample_state().with_quantity('demand','store_y','monitors',6))
        old=session.preview(); session.confirm(old)
        reopened=RestockSession.open(JsonStore(self.path))
        self.assertEqual(reopened.state,session.state)
        self.assertIsNone(reopened.pending_preview)
        self.assertEqual(reopened.state.demand['store_y']['monitors'],2)
        with self.assertRaises(PreviewError): reopened.confirm(old)
        reopened.edit_quantity('inventory','warehouse_b','monitors',2,'add')
        preview=reopened.preview(); self.assertEqual(preview.plan.total_cost_cents,200)
        reopened.confirm(preview)
        self.assertEqual(self.store.load().demand['store_y']['monitors'],0)

    def test_fresh_process_reads_saved_demand(self):
        session=self.start(sample_state().with_quantity('demand','store_y','monitors',6))
        session.confirm(session.preview())
        code='from storage import JsonStore; import sys; s=JsonStore(sys.argv[1]).load(); print(s.demand["store_y"]["monitors"], s.revision)'
        result=subprocess.run([sys.executable,'-B','-c',code,str(self.path)],
                              cwd=Path(__file__).resolve().parents[1],text=True,capture_output=True,check=True)
        self.assertEqual(result.stdout.strip(),f'2 {session.state.revision}')

    def test_preview_cancel_and_noops_never_write(self):
        session=self.start(); saved=self.path.read_bytes()
        with patch.object(self.store,'commit',side_effect=AssertionError('unexpected write')):
            p=session.preview(); session.cancel(p)
            session.edit_quantity('inventory','warehouse_a','keyboards',5)
            session.edit_shipping_cost('warehouse_a','store_x',200)
        self.assertEqual(self.path.read_bytes(),saved)

    def test_stale_second_session_and_manual_same_revision_change(self):
        first=self.start(); second=RestockSession.open(self.store)
        stale=second.preview(); first.edit_shipping_cost('warehouse_a','store_x',1)
        with self.assertRaises(StorageConflict): second.confirm(stale)
        self.assertIs(second.pending_preview,stale)
        self.assertEqual(self.store.load(),first.state)
        second.reload()
        with self.assertRaises(PreviewError): second.confirm(stale)
        pending=second.preview()
        data=self.store.load().to_dict(); data['shipping_costs_cents']['warehouse_a']['store_x']=2
        self.path.write_text(json.dumps(data))
        with self.assertRaises(StorageConflict): second.confirm(pending)

    def test_failed_reload_preserves_current_session(self):
        session=self.start(); pending=session.preview(); old=session.state
        self.path.write_text('{broken')
        with self.assertRaises(StorageError): session.reload()
        self.assertIs(session.state,old); self.assertIs(session.pending_preview,pending)
        with self.assertRaises(StorageError): session.confirm(pending)
        self.assertEqual(self.path.read_text(),'{broken')

    def test_malformed_files_rejected_without_reset(self):
        for payload in [b'',b'{',b'[]',b'null',b'\xff',b'{"revision":0,"revision":1}']:
            self.path.write_bytes(payload)
            with self.assertRaises(StorageError): self.store.load()
            with self.assertRaises(StorageError): self.store.initialize(sample_state())
            self.assertEqual(self.path.read_bytes(),payload)
        data=sample_state().to_dict(); data['demand']['store_x']['keyboards']=-1
        self.path.write_text(json.dumps(data))
        with self.assertRaises(StorageError): self.store.load()

    def test_write_flush_fsync_and_replace_failures(self):
        session=self.start(); pending=session.preview(); old=session.state; saved=self.path.read_bytes()
        real_factory=tempfile.NamedTemporaryFile
        class FailingFile:
            def __init__(self,step,**kwargs): self.file=real_factory(**kwargs); self.step=step
            def __enter__(self): return self
            def __exit__(self,*args): self.file.close()
            @property
            def name(self): return self.file.name
            def write(self,payload):
                if self.step=='write':
                    self.file.write(payload[:20]); raise OSError('injected partial write')
                return self.file.write(payload)
            def flush(self):
                if self.step=='flush': raise OSError('injected flush failure')
                return self.file.flush()
            def fileno(self): return self.file.fileno()
        for step in ['create','write','flush','fsync','replace']:
            if step=='create': manager=patch('storage.tempfile.NamedTemporaryFile',side_effect=OSError('injected create failure'))
            elif step in ('write','flush'):
                manager=patch('storage.tempfile.NamedTemporaryFile',side_effect=lambda **kw:FailingFile(step,**kw))
            else: manager=patch(f'storage.os.{step}',side_effect=OSError(f'injected {step} failure'))
            with self.subTest(step=step),manager,self.assertRaises(StorageError): session.confirm(pending)
            self.assertEqual(self.path.read_bytes(),saved)
            self.assertIs(session.state,old); self.assertIs(session.pending_preview,pending)
            self.assertEqual(list(self.path.parent.glob('*.tmp')),[])
        session.confirm(pending)
        self.assertEqual(self.store.load(),session.state)

    def test_interruption_after_publication_never_double_deducts(self):
        session=self.start(); pending=session.preview(); old=session.state
        original=self.store.commit
        def publish_then_interrupt(expected,candidate):
            original(expected,candidate)
            raise RuntimeError('simulated lost acknowledgment after successful publication')
        with patch.object(self.store,'commit',side_effect=publish_then_interrupt),self.assertRaises(RuntimeError):
            session.confirm(pending)
        self.assertIs(session.state,old)
        committed=self.store.load()
        self.assertEqual(committed.revision,old.revision+1)
        with self.assertRaises(StorageConflict): session.confirm(pending)
        self.assertEqual(self.store.load(),committed)
        session.reload()
        self.assertEqual(session.state,committed)
        with self.assertRaises(PreviewError): session.confirm(pending)

    def test_reset_preserves_sample_and_blocks_old_preview(self):
        sample_bytes=SAMPLE_PATH.read_bytes()
        session=self.start(); preview=session.preview(); session.confirm(preview)
        before=session.state.revision; session.reset(sample_state())
        self.assertEqual(session.state.revision,before+1)
        self.assertEqual(session.state.inventory,sample_state().inventory)
        self.assertEqual(self.store.load(),session.state)
        self.assertEqual(SAMPLE_PATH.read_bytes(),sample_bytes)
        with self.assertRaises(PreviewError): session.confirm(preview)
        self.assertEqual(list(self.path.parent.glob('*.tmp')),[])

    def test_protected_targets_symlinks_and_missing_parent(self):
        before=SAMPLE_PATH.read_bytes()
        with self.assertRaises(StorageError): JsonStore(SAMPLE_PATH)
        with self.assertRaises(StorageError): JsonStore(SAMPLE_PATH.parent/'..'/'data'/'sample.json')
        with self.assertRaises(StorageError): JsonStore(self.path.with_suffix('.pdf'))
        self.path.symlink_to(SAMPLE_PATH)
        with self.assertRaises(StorageError): JsonStore(self.path)
        loop=Path(self.temp.name)/'loop'
        loop.symlink_to(loop)
        with self.assertRaises(StorageError): JsonStore(loop/'state.json')
        with self.assertRaises(StorageError): JsonStore(Path(self.temp.name)/'missing'/'x.json').initialize(sample_state())
        self.assertEqual(SAMPLE_PATH.read_bytes(),before)

    def test_commit_revision_catalog_and_type_checks(self):
        self.start(); old=self.store.load()
        for expected,candidate in [(None,old),(old,None),(old,old)]:
            with self.assertRaises(StorageError): self.store.commit(expected,candidate)
        data=old.to_dict(); data['revision']+=2
        with self.assertRaises(StorageError): self.store.commit(old,State.from_dict(data))
        data=old.to_dict(); data['revision']+=1
        data['items']['new']='New item'
        for table in ['inventory','demand']:
            for row in data[table].values(): row['new']=0
        with self.assertRaises(StorageError): self.store.commit(old,State.from_dict(data))
        self.assertEqual(self.store.load(),old)

    def test_failed_edits_reset_and_missing_save_preserve_session(self):
        session=self.start(); old=session.state; preview=session.preview(); saved=self.path.read_bytes()
        with patch('storage.os.replace',side_effect=OSError('injected commit failure')):
            for action in [lambda:session.edit_quantity('inventory','warehouse_a','keyboards',6),
                           lambda:session.edit_shipping_cost('warehouse_a','store_x',1),
                           lambda:session.reset(sample_state())]:
                with self.assertRaises(StorageError): action()
                self.assertIs(session.state,old); self.assertIs(session.pending_preview,preview)
                self.assertEqual(self.path.read_bytes(),saved)
        self.path.unlink()
        with self.assertRaises(StorageError): session.confirm(preview)
        self.assertFalse(self.path.exists())
        self.assertIs(session.state,old); self.assertIs(session.pending_preview,preview)

    def test_unicode_and_numeric_boundary_roundtrip(self):
        from data_model import MAX_STATE_INTEGER
        data=sample_state().to_dict()
        data['items']['keyboards']='Claviers — لوحات المفاتيح'
        data['inventory']['warehouse_a']['keyboards']=MAX_STATE_INTEGER
        data['shipping_costs_cents']['warehouse_a']['store_x']=MAX_STATE_INTEGER
        state=State.from_dict(data)
        self.store.initialize(state)
        self.assertEqual(self.store.load(),state)

    def test_leftover_temp_not_loaded_and_cleanup_error_not_false_failure(self):
        self.path.parent.joinpath('.state.json.orphan.tmp').write_text('broken abandoned temporary file')
        session=self.start()
        self.assertEqual(session.state,sample_state())
        # Replacement succeeded: an error removing the now-absent temporary path
        # must not be reported as a failed state commit.
        with patch('storage.Path.unlink',side_effect=OSError('injected cleanup error')):
            session.confirm(session.preview())
        self.assertEqual(self.store.load(),session.state)


if __name__=='__main__': unittest.main()
