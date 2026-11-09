"""Finite state-machine audit plus actual process interruptions and mutation tests."""
import io
from itertools import product
from pathlib import Path
import subprocess
import sys
import tempfile
import types
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from data_model import State
from operations import RestockSession, PreviewError
from storage import JsonStore
from test_optimizer import single_item_state
from test_operations import sample_state
import test_operations
import test_storage


def persistent_traces():
    actions=('preview','confirm','cancel','stock','demand','price','reset','reopen')
    checked=0
    with tempfile.TemporaryDirectory() as folder:
        path=Path(folder)/'state.json'; store=JsonStore(path)
        for trace in product(actions,repeat=3):
            path.unlink(missing_ok=True)
            initial=single_item_state([2],[3],[[1]])
            store.initialize(initial); session=RestockSession.open(store)
            stock,demand,price,revision=2,3,1,0
            active=False; handle=None
            for action in trace:
                if action=='preview': handle=session.preview(); active=True
                elif action=='confirm':
                    allowed=active and min(stock,demand)>0
                    if allowed:
                        q=min(stock,demand); stock-=q; demand-=q; revision+=1; active=False
                        session.confirm(handle)
                    else:
                        try: session.confirm(handle)
                        except PreviewError: pass
                        else: raise AssertionError(('unexpected confirmation',trace))
                elif action=='cancel':
                    if active: session.cancel(handle); active=False
                    else:
                        try: session.cancel(handle)
                        except PreviewError: pass
                        else: raise AssertionError(('unexpected cancellation',trace))
                elif action=='stock':
                    stock+=1; revision+=1; active=False
                    session.edit_quantity('inventory','w0','i',1,'add')
                elif action=='demand':
                    demand+=1; revision+=1; active=False
                    session.edit_quantity('demand','s0','i',1,'add')
                elif action=='price':
                    price=3-price; revision+=1; active=False
                    session.edit_shipping_cost('w0','s0',price)
                elif action=='reset':
                    stock,demand,price=2,3,1; revision+=1; active=False
                    session.reset(initial)
                else:
                    session=RestockSession.open(JsonStore(path)); active=False
                expected=(stock,demand,price,revision)
                for state in [session.state,store.load()]:
                    assert (state.inventory['w0']['i'],state.demand['s0']['i'],
                            state.shipping_costs_cents['w0']['s0'],state.revision)==expected,trace
                assert (session.pending_preview is not None)==active,trace
            checked+=1
    print(f'PASS: all {checked} length-three persistent traces over eight actions; disk/memory/model agree at every step')


def actual_process_interruptions():
    code='''
import os,sys
from storage import JsonStore
from operations import RestockSession
import storage
session=RestockSession.open(JsonStore(sys.argv[1]))
preview=session.preview()
real_replace=storage.os.replace
def interrupted(source,target):
    if sys.argv[2]=='before': os._exit(23)
    real_replace(source,target)
    os._exit(24)
storage.os.replace=interrupted
session.confirm(preview)
raise AssertionError('Interruption hook was not reached')
'''
    for phase,exitcode in [('before',23),('after',24)]:
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'state.json'; store=JsonStore(path)
            initial=sample_state().with_quantity('demand','store_y','monitors',6)
            store.initialize(initial)
            expected_session=RestockSession(initial)
            expected=expected_session.confirm(expected_session.preview())
            result=subprocess.run([sys.executable,'-B','-c',code,str(path),phase],cwd=ROOT,
                                  text=True,capture_output=True,timeout=15)
            assert result.returncode==exitcode,(phase,result.stderr)
            loaded=store.load()
            assert loaded==(initial if phase=='before' else expected)
            reopened=RestockSession.open(store)
            assert reopened.pending_preview is None
            if phase=='after':
                assert reopened.state.demand['store_y']['monitors']==2
                assert not reopened.preview().can_confirm
            else:
                assert list(path.parent.glob('*.tmp')), 'Expected interrupted staging file'
            print(f'PASS: actual process exit {phase} replacement; recovered complete '+('old' if phase=='before' else 'new')+' state')


def mutation_checks():
    source=(ROOT/'operations.py').read_text()
    variants=[('active preview check removed',
               'if preview is None or preview is not self._pending:', 'if False:'),
              ('source snapshot check removed','if plan.source_state != state:', 'if False:'),
              ('persistent commit skipped','self._store.commit(self._state, candidate)', 'pass')]
    original_ops=test_operations.RestockSession
    original_storage=test_storage.RestockSession
    original_apply=test_operations.apply_restock
    original_validate=test_operations.validate_plan
    original_error=test_operations.PreviewError
    try:
        for index,(label,old,new) in enumerate(variants):
            assert source.count(old)==1
            name=f'_transaction_mutant_{index}'; module=types.ModuleType(name); sys.modules[name]=module
            try:
                exec(compile(source.replace(old,new),name,'exec'),module.__dict__)
                test_operations.RestockSession=module.RestockSession
                test_operations.apply_restock=module.apply_restock
                test_operations.validate_plan=module.validate_plan
                test_operations.PreviewError=module.PreviewError
                test_storage.RestockSession=module.RestockSession
                if index==0:
                    suite=unittest.TestSuite([test_operations.OperationsTests('test_handle_identity_replacement_foreign_and_reset_replay')])
                elif index==1:
                    suite=unittest.TestSuite([test_operations.OperationsTests('test_full_snapshot_not_just_revision')])
                else:
                    suite=unittest.TestSuite([test_storage.StorageTests('test_reset_preserves_sample_and_blocks_old_preview')])
                result=unittest.TextTestRunner(stream=io.StringIO()).run(suite)
                assert not result.wasSuccessful(),f'Missed mutation: {label}'
                assert result.failures, f'Only incidental errors, no assertion caught: {label}'
                print(f'PASS: tests detected deliberately {label}')
            finally: del sys.modules[name]
    finally:
        test_operations.RestockSession=original_ops
        test_operations.apply_restock=original_apply
        test_operations.validate_plan=original_validate
        test_operations.PreviewError=original_error
        test_storage.RestockSession=original_storage


if __name__=='__main__':
    persistent_traces()
    actual_process_interruptions()
    mutation_checks()
