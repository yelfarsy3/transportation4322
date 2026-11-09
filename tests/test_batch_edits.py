from itertools import product
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

from data_model import ValidationError
from operations import RestockSession, PreviewError
from storage import JsonStore, StorageError
from test_operations import sample_state


class BatchEditTests(unittest.TestCase):
    def test_multiple_tables_one_revision_one_save(self):
        with tempfile.TemporaryDirectory() as folder:
            store=JsonStore(Path(folder)/'state.json'); store.initialize(sample_state())
            session=RestockSession.open(store); old=session.state; preview=session.preview()
            data=old.to_dict()
            data['inventory']['warehouse_a']['keyboards']=8
            data['inventory']['warehouse_b']['monitors']=10
            data['demand']['store_y']['monitors']=6
            data['shipping_costs_cents']['warehouse_a']['store_x']=125
            with patch.object(store,'commit',wraps=store.commit) as commit:
                session.edit_tables(expected_state=old,inventory=data['inventory'],demand=data['demand'],
                                    shipping_costs_cents=data['shipping_costs_cents'])
                self.assertEqual(commit.call_count,1)
            self.assertEqual(session.state.revision,1)
            self.assertEqual(session.state,store.load())
            self.assertEqual(session.state.inventory['warehouse_b']['monitors'],10)
            self.assertEqual(session.state.shipping_costs_cents['warehouse_a']['store_x'],125)
            with self.assertRaises(PreviewError): session.confirm(preview)
            self.assertEqual(old,sample_state())

    def test_one_bad_cell_rejects_entire_batch(self):
        for invalid in [-1,1.5,True,None,'3']:
            session=RestockSession(sample_state()); old=session.state; preview=session.preview()
            data=old.to_dict(); data['inventory']['warehouse_a']['keyboards']=9
            data['demand']['store_y']['monitors']=invalid
            with self.assertRaises(ValidationError):
                session.edit_tables(expected_state=old,inventory=data['inventory'],demand=data['demand'])
            self.assertIs(session.state,old); self.assertIs(session.pending_preview,preview)

    def test_failure_noop_and_stale_draft(self):
        session=RestockSession(sample_state()); old=session.state; preview=session.preview()
        self.assertIs(session.edit_tables(expected_state=old,inventory=old.inventory),old)
        self.assertIs(session.pending_preview,preview)
        session.edit_shipping_cost('warehouse_a','store_x',1)
        with self.assertRaises(ValidationError): session.edit_tables(expected_state=old,demand=old.demand)
        with tempfile.TemporaryDirectory() as folder:
            store=JsonStore(Path(folder)/'state.json'); store.initialize(old)
            session=RestockSession.open(store); preview=session.preview(); data=old.to_dict()
            data['inventory']['warehouse_a']['keyboards']=99
            data['demand']['store_y']['monitors']=6
            saved=store.path.read_bytes()
            with patch('storage.os.replace',side_effect=OSError('injected failure')),self.assertRaises(StorageError):
                session.edit_tables(expected_state=old,inventory=data['inventory'],demand=data['demand'])
            self.assertEqual(session.state,old); self.assertIs(session.pending_preview,preview)
            self.assertEqual(store.path.read_bytes(),saved)

    def test_exhaustive_four_cell_batches(self):
        for values in product(range(3),repeat=4):
            session=RestockSession(sample_state()); data=session.state.to_dict()
            for row, pair in zip(data['inventory'].values(),[values[:2],values[2:]]):
                row.update(zip(row,pair))
            session.edit_tables(expected_state=session.state,inventory=data['inventory'])
            self.assertEqual(session.state.inventory,data['inventory'])
            self.assertEqual(session.state.demand,sample_state().demand)
            self.assertEqual(session.state.revision,1)
