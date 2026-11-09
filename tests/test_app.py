"""Actual Streamlit script tests. Grid edit events injected via public session state.
Live browser checks supplement AppTest, which cannot type into canvas cells.
"""
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from streamlit.testing.v1 import AppTest
from storage import JsonStore
from test_operations import sample_state

APP=Path(__file__).resolve().parents[1]/'app.py'

class AppWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.folder=tempfile.TemporaryDirectory(); self.addCleanup(self.folder.cleanup)
        self.store=JsonStore(Path(self.folder.name)/'state.json'); self.store.initialize(sample_state())
        env=patch.dict(os.environ,{'TRANSPORTATION_STATE_PATH':str(self.store.path)})
        env.start(); self.addCleanup(env.stop)
        self.app=AppTest.from_file(APP).run(timeout=20)
        self.clean()

    def clean(self):
        self.assertEqual(len(self.app.exception),0, str(self.app.exception))

    def click(self,key):
        self.app.button(key=key).click().run(timeout=20); self.clean()

    def edit(self,table,edits):
        key=f'{table}_{self.app.session_state.epoch}'
        self.app.session_state[key]={'edited_rows':edits,'added_rows':[],'deleted_rows':[]}

    def test_full_preview_cancel_confirm_and_restart(self):
        original=self.store.path.read_bytes()
        self.click('preview')
        self.assertEqual(self.app.header[0].value,'Restock preview')
        self.assertIn('$14.00',' '.join(x.value for x in self.app.markdown))
        self.assertEqual(self.store.path.read_bytes(),original)
        self.click('cancel'); self.assertEqual(self.store.path.read_bytes(),original)
        self.click('preview'); self.click('confirm')
        self.assertEqual(self.store.load().revision,1)
        self.assertEqual(sum(sum(r.values()) for r in self.store.load().demand.values()),0)
        self.assertEqual(len([b for b in self.app.button if b.key=='confirm']),0)
        self.click('back'); self.click('preview')
        self.assertTrue(self.app.button(key='confirm').disabled)
        self.app=AppTest.from_file(APP).run(); self.clean()
        self.assertEqual(self.app.session_state.controller.state,self.store.load())

    def test_partial_all_five_screens_and_persisted_unmet_demand(self):
        self.edit('demand',{1:{'v1':'6'}}); self.click('save'); self.click('preview')
        self.assertEqual(self.app.header[0].value,'Partial restock preview')
        self.assertIn('$20.00',' '.join(x.value for x in self.app.markdown))
        self.assertEqual(self.app.button(key='confirm').label,'Approve partial restock')
        self.click('confirm')
        self.assertIn('12 units allocated; 2 units outstanding',self.app.success[0].value)
        self.assertEqual(self.store.load().demand['store_y']['monitors'],2)
        self.app=AppTest.from_file(APP).run(); self.clean(); self.click('preview')
        self.assertTrue(self.app.button(key='confirm').disabled)
        self.assertEqual(self.app.info[0].value,'Nothing available to ship.')

    def test_multi_table_save_and_dirty_preview_guard(self):
        self.edit('inventory',{0:{'v0':'8'},1:{'v1':'10'}})
        self.edit('demand',{1:{'v1':'6'}})
        self.edit('shipping_costs_cents',{0:{'v0':'1.25'}})
        self.click('preview'); self.assertTrue(self.app.error)
        self.assertEqual(self.store.load(),sample_state())
        self.click('save'); state=self.store.load()
        self.assertEqual((state.inventory['warehouse_a']['keyboards'],state.inventory['warehouse_b']['monitors'],
                          state.demand['store_y']['monitors'],state.shipping_costs_cents['warehouse_a']['store_x']), (8,10,6,125))
        self.assertEqual(state.revision,1)
        self.click('save'); self.assertEqual(self.store.load().revision,1)

    def test_bad_cell_rejects_every_edit_and_discard_recovers(self):
        self.edit('inventory',{0:{'v0':'8'}}); self.edit('shipping_costs_cents',{1:{'v1':'1.001'}})
        self.click('save'); self.assertTrue(self.app.error); self.assertEqual(self.store.load(),sample_state())
        self.click('discard'); self.click('preview')
        self.assertEqual(self.app.session_state.controller.pending_preview.plan.total_cost_cents,1400)

    def test_quantity_shortcut_add_remove_set_and_invalid(self):
        self.app.text_input[0].set_value('3'); self.click('quick')
        self.assertEqual(self.store.load().inventory['warehouse_a']['keyboards'],8)
        self.app.selectbox[2].select('remove'); self.app.text_input[0].set_value('9'); self.click('quick')
        self.assertTrue(self.app.error); self.assertEqual(self.store.load().revision,1)
        self.app.text_input[0].set_value('2'); self.click('quick')
        self.assertEqual(self.store.load().inventory['warehouse_a']['keyboards'],6)
        self.app.selectbox[0].select(('demand','store_y')); self.app.selectbox[1].select('monitors')
        self.app.selectbox[2].select('set'); self.app.text_input[0].set_value('6'); self.click('quick')
        self.assertEqual(self.store.load().demand['store_y']['monitors'],6)

    def test_dirty_shortcut_is_blocked(self):
        self.edit('inventory',{0:{'v0':'8'}}); self.app.text_input[0].set_value('3'); self.click('quick')
        self.assertTrue(self.app.error); self.assertEqual(self.store.load(),sample_state())

    def test_reset_requires_confirmation_and_clears_preview(self):
        self.click('reset'); self.assertTrue(self.app.error); self.assertEqual(self.store.load().revision,0)
        self.click('preview'); self.app.checkbox[0].check(); self.click('reset')
        self.assertEqual(self.store.load().revision,1)
        self.assertIsNone(self.app.session_state.controller.pending_preview)
        self.assertFalse(self.app.checkbox[0].value)

    def test_failed_save_blocks_changes_until_reload(self):
        self.edit('inventory',{0:{'v0':'8'}})
        with patch('storage.os.replace',side_effect=OSError('injected')): self.click('save')
        self.assertTrue(self.app.session_state.blocked); self.assertEqual(self.store.load(),sample_state())
        self.app.run(); self.assertTrue(self.app.button(key='save').disabled)
        self.click('reload'); self.assertFalse(self.app.session_state.blocked)
        self.assertEqual(self.app.session_state.controller.state,sample_state())

    def test_stale_disk_confirmation_never_deducts(self):
        self.click('preview')
        old=self.store.load(); other=old.with_quantity('inventory','warehouse_a','keyboards',99)
        self.store.commit(old,other)
        self.click('confirm'); self.assertTrue(self.app.error); self.assertEqual(self.store.load(),other)
        self.click('reload'); self.assertIsNone(self.app.session_state.controller.pending_preview)
        self.assertEqual(self.app.session_state.controller.state,other)

    def test_corrupt_save_reload_and_startup_preserve_file(self):
        self.click('preview'); self.store.path.write_text('{broken')
        self.click('reload'); self.assertTrue(self.app.error); self.assertTrue(self.app.session_state.blocked)
        self.app=AppTest.from_file(APP).run(); self.clean(); self.assertTrue(self.app.error)
        self.assertEqual(self.store.path.read_text(),'{broken')
        self.assertFalse(any(b.key=='initialize' for b in self.app.button))

    def test_first_run_is_explicit(self):
        self.store.path.unlink()
        self.app=AppTest.from_file(APP).run(); self.clean()
        self.assertFalse(self.store.path.exists()); self.click('initialize')
        self.assertEqual(self.store.load(),sample_state())

    def test_exact_large_values_remain_text(self):
        big=2**53+1
        self.edit('inventory',{0:{'v0':str(big)}}); self.edit('shipping_costs_cents',{0:{'v0':f'{big}.01'}})
        self.click('save'); self.assertEqual(self.store.load().inventory['warehouse_a']['keyboards'],big)
        self.assertEqual(self.store.load().shipping_costs_cents['warehouse_a']['store_x'],big*100+1)
        self.click('preview'); self.clean()

    def test_missing_parent_reports_error_without_creating_it(self):
        with patch.dict(os.environ,{'TRANSPORTATION_STATE_PATH':str(Path(self.folder.name)/'absent'/'save.json')}):
            self.app=AppTest.from_file(APP).run(); self.clean(); self.assertTrue(self.app.error)
            self.assertFalse((Path(self.folder.name)/'absent').exists())

    def test_failed_confirmation_then_reload_requires_new_preview(self):
        self.click('preview')
        with patch('storage.os.replace',side_effect=OSError('injected')): self.click('confirm')
        self.assertEqual(self.store.load(),sample_state())
        self.assertTrue(self.app.session_state.blocked)
        self.app.run(); self.assertTrue(self.app.button(key='confirm').disabled)
        self.click('reload'); self.click('preview'); self.click('confirm')
        self.assertEqual(self.store.load().revision,1)

    def test_stale_edit_rejected_and_reload_discards_draft(self):
        self.edit('inventory',{0:{'v0':'8'}})
        old=self.store.load(); other=old.with_shipping_cost('warehouse_a','store_x',125)
        self.store.commit(old,other)
        self.click('save'); self.assertTrue(self.app.error); self.assertEqual(self.store.load(),other)
        self.click('reload'); self.click('save'); self.assertEqual(self.store.load(),other)

    def test_every_binary_supply_demand_combination_through_ui(self):
        from itertools import product
        from data_model import State
        from brute_force_reference import solve_tiny
        from ui_model import rows_for
        for a,b,x,y in product(range(2),repeat=4):
            with self.subTest(supply=(a,b),demand=(x,y)):
                state=State({'i':'Item'},{'a':'A','b':'B'},{'x':'X','y':'Y'},
                            {'a':{'i':a},'b':{'i':b}},{'x':{'i':x},'y':{'i':y}},
                            {'a':{'x':1,'y':2},'b':{'x':2,'y':100}})
                self.store.path.write_text(__import__('json').dumps(state.to_dict()))
                self.app=AppTest.from_file(APP).run(); self.clean(); self.click('preview')
                expected=solve_tiny([a,b],[x,y],[[1,2],[2,100]])
                plan=self.app.session_state.controller.pending_preview.plan
                self.assertEqual((plan.units_shipped,plan.total_cost_cents),(expected.units,expected.cost_cents))
                projected=self.app.dataframe[-2].value.to_dict('records')
                unmet=self.app.dataframe[-1].value.to_dict('records')
                self.assertEqual(projected,rows_for(plan.projected_inventory,state.warehouses,state.items))
                self.assertEqual(unmet,rows_for(plan.remaining_demand,state.stores,state.items))
                self.assertEqual(self.store.load(),state)
                if expected.units:
                    self.click('confirm')
                    saved=self.store.load()
                    self.assertEqual(saved.inventory,plan.projected_inventory)
                    self.assertEqual(saved.demand,plan.remaining_demand)
                else:
                    self.assertTrue(self.app.button(key='confirm').disabled)

    def test_maximum_supported_cells_render_and_preview_exactly(self):
        from data_model import MAX_STATE_INTEGER
        from ui_model import money
        self.edit('inventory',{0:{'v0':str(MAX_STATE_INTEGER)}})
        self.edit('shipping_costs_cents',{0:{'v0':money(MAX_STATE_INTEGER)}})
        self.click('save'); self.click('preview')
        self.assertEqual(self.app.session_state.controller.state.inventory['warehouse_a']['keyboards'],MAX_STATE_INTEGER)
