from dataclasses import replace
from itertools import product
from pathlib import Path
import unittest

from data_model import State, ValidationError, MAX_STATE_INTEGER
from optimizer import compute_restock_plan
from operations import RestockSession, PreviewError, validate_plan, apply_restock
from test_optimizer import single_item_state


def sample_state():
    return State.from_json((Path(__file__).resolve().parents[1]/'data/sample.json').read_text())


class OperationsTests(unittest.TestCase):
    def test_preview_cancel_and_repeated_confirmation(self):
        state=sample_state(); session=RestockSession(state)
        preview=session.preview()
        self.assertIs(session.state,state)
        session.cancel(preview)
        self.assertIs(session.state,state)
        with self.assertRaises(PreviewError): session.confirm(preview)
        preview=session.preview()
        updated=session.confirm(preview)
        self.assertEqual(updated.revision,1)
        self.assertEqual(sum(sum(row.values()) for row in updated.demand.values()),0)
        self.assertEqual(sum(sum(row.values()) for row in updated.inventory.values()),4)
        with self.assertRaises(PreviewError): session.confirm(preview)
        self.assertIs(session.state,updated)

    def test_partial_then_replenish_then_complete(self):
        session=RestockSession(sample_state().with_quantity('demand','store_y','monitors',6))
        preview=session.preview()
        self.assertEqual(preview.plan.total_cost_cents,2000)
        session.confirm(preview)
        self.assertEqual(session.state.demand['store_y']['monitors'],2)
        empty=session.preview()
        self.assertFalse(empty.can_confirm)
        with self.assertRaises(PreviewError): session.confirm(empty)
        session.edit_quantity('inventory','warehouse_b','monitors',2,'add')
        last=session.preview()
        self.assertEqual((last.plan.units_shipped,last.plan.total_cost_cents),(2,200))
        session.confirm(last)
        self.assertEqual(session.state.demand['store_y']['monitors'],0)

    def test_all_changes_invalidate_but_noops_and_failures_preserve_preview(self):
        actions=[lambda s:s.edit_quantity('inventory','warehouse_a','keyboards',6),
                 lambda s:s.edit_quantity('demand','store_x','keyboards',4),
                 lambda s:s.edit_shipping_cost('warehouse_a','store_x',201),
                 lambda s:s.reset(sample_state())]
        for action in actions:
            session=RestockSession(sample_state()); old=session.preview()
            action(session)
            with self.assertRaises(PreviewError): session.confirm(old)
        session=RestockSession(sample_state()); preview=session.preview()
        session.edit_quantity('inventory','warehouse_a','keyboards',5)
        session.edit_shipping_cost('warehouse_a','store_x',200)
        with self.assertRaises(ValidationError): session.edit_quantity('inventory','warehouse_a','keyboards',99,'remove')
        self.assertIs(session.pending_preview,preview)
        session.confirm(preview)

    def test_handle_identity_replacement_foreign_and_reset_replay(self):
        session=RestockSession(sample_state()); old=session.preview(); new=session.preview()
        for invalid in [old, replace(new), RestockSession(session.state).preview(), None]:
            with self.assertRaises(PreviewError): session.confirm(invalid)
        session.confirm(new); session.reset(sample_state())
        with self.assertRaises(PreviewError): session.confirm(new)
        with self.assertRaises(PreviewError): session.cancel(new)

    def test_full_snapshot_not_just_revision(self):
        state=sample_state()
        a=state.with_shipping_cost('warehouse_a','store_x',1)
        b=state.with_shipping_cost('warehouse_a','store_x',2)
        self.assertEqual(a.revision,b.revision)
        with self.assertRaises(ValidationError): apply_restock(b,compute_restock_plan(a))

    def test_corrupt_plan_fields_and_projections(self):
        state=sample_state(); plan=compute_restock_plan(state); first=plan.shipments[0]
        bad=[replace(plan,units_shipped=True),replace(plan,units_shipped=9),
             replace(plan,total_cost_cents=1399),replace(plan,total_cost_cents=1400.0),
             replace(plan,shipments=plan.shipments+(first,)),replace(plan,shipments=()),
             replace(plan,projected_inventory=state.inventory),replace(plan,remaining_demand={})]
        for value in [-1,0,True,1.5,99]:
            bad.append(replace(plan,shipments=(replace(first,quantity=value),)+plan.shipments[1:]))
        for field,value in [('item_id','wrong'),('warehouse_id',[]),('store_id','wrong'),('unit_cost_cents',1)]:
            bad.append(replace(plan,shipments=(replace(first,**{field:value}),)+plan.shipments[1:]))
        data={w:dict(row) for w,row in plan.projected_inventory.items()}
        data['warehouse_a']['monitors']=True
        bad.append(replace(plan,projected_inventory=data))
        for candidate in bad:
            with self.subTest(candidate=candidate),self.assertRaises(ValidationError): validate_plan(state,candidate)
        self.assertEqual(state,sample_state())

    def test_empty_plan_and_revision_overflow_do_not_change_state(self):
        for stock,need in [(0,0),(0,4),(4,0)]:
            session=RestockSession(single_item_state([stock],[need],[[0]])); old=session.state
            preview=session.preview()
            with self.assertRaises(PreviewError): session.confirm(preview)
            self.assertIs(session.state,old)
        data=sample_state().to_dict(); data['revision']=MAX_STATE_INTEGER
        session=RestockSession(State.from_dict(data)); old=session.state; preview=session.preview()
        with self.assertRaises(ValidationError): session.confirm(preview)
        self.assertIs(session.state,old); self.assertIs(session.pending_preview,preview)

    def test_exhaustive_tiny_confirm_and_cancel(self):
        for cells in product(range(3),repeat=4):
            state=single_item_state(cells[:2],cells[2:],[[0,3],[2,1]])
            for method in ['dijkstra','bellman_ford']:
                session=RestockSession(state); canceled=session.preview(method=method)
                session.cancel(canceled); self.assertEqual(session.state,state)
                preview=session.preview(method=method)
                if preview.can_confirm:
                    updated=session.confirm(preview)
                    self.assertEqual(updated.inventory,preview.plan.projected_inventory)
                    self.assertEqual(updated.demand,preview.plan.remaining_demand)
                    self.assertEqual(updated.revision,state.revision+1)
                    with self.assertRaises(PreviewError): session.confirm(preview)
                else:
                    with self.assertRaises(PreviewError): session.confirm(preview)

    def test_exhaustive_action_sequences_against_scalar_model(self):
        actions=('preview','confirm','cancel','stock','demand','price','reset')
        for trace in product(actions,repeat=4):
            initial=single_item_state([2],[3],[[1]])
            session=RestockSession(initial)
            stock,demand,price,revision=2,3,1,0
            active=False; handle=None
            for action in trace:
                if action=='preview':
                    handle=session.preview(); active=True
                elif action=='confirm':
                    if active and min(stock,demand)>0:
                        q=min(stock,demand); stock-=q; demand-=q; revision+=1; active=False
                        session.confirm(handle)
                    else:
                        with self.assertRaises(PreviewError): session.confirm(handle)
                elif action=='cancel':
                    if active: session.cancel(handle); active=False
                    else:
                        with self.assertRaises(PreviewError): session.cancel(handle)
                elif action=='stock':
                    stock+=1; revision+=1; active=False
                    session.edit_quantity('inventory','w0','i',1,'add')
                elif action=='demand':
                    demand+=1; revision+=1; active=False
                    session.edit_quantity('demand','s0','i',1,'add')
                elif action=='price':
                    price=3-price; revision+=1; active=False
                    session.edit_shipping_cost('w0','s0',price)
                else:
                    stock,demand,price=2,3,1; revision+=1; active=False
                    session.reset(initial)
                with self.subTest(trace=trace,action=action):
                    self.assertEqual((session.state.inventory['w0']['i'],session.state.demand['s0']['i'],
                                      session.state.shipping_costs_cents['w0']['s0'],session.state.revision),
                                     (stock,demand,price,revision))
                    self.assertEqual(session.pending_preview is not None,active)
if __name__=='__main__': unittest.main()
