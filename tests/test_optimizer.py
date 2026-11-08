from dataclasses import FrozenInstanceError
from itertools import product
from pathlib import Path
import random
import unittest

from brute_force_reference import solve_tiny
from data_model import MAX_STATE_INTEGER, State
from optimizer import compute_restock_plan, _solve_item


def single_item_state(stock, need, costs):
    warehouses = {f'w{w}': f'Warehouse {w}' for w in range(len(stock))}
    stores = {f's{s}': f'Store {s}' for s in range(len(need))}
    return State({'i': 'Item'}, warehouses, stores,
                 {w: {'i': stock[j]} for j,w in enumerate(warehouses)},
                 {s: {'i': need[j]} for j,s in enumerate(stores)},
                 {w: dict(zip(stores,costs[j])) for j,w in enumerate(warehouses)})


def assert_plan(test, state, plan):
    """Recompute feasibility/cost/projections independently from positive shipments."""
    inventory = {w: dict(row) for w,row in state.inventory.items()}
    demand = {s: dict(row) for s,row in state.demand.items()}
    by_item = dict.fromkeys(state.items,0)
    seen = set()
    cost = units = 0
    test.assertIs(plan.source_state, state)
    for shipment in plan.shipments:
        item,w,s,q = shipment.item_id,shipment.warehouse_id,shipment.store_id,shipment.quantity
        test.assertIn(item,state.items)
        test.assertIn(w,state.warehouses)
        test.assertIn(s,state.stores)
        test.assertIs(type(q),int)
        test.assertGreater(q,0)
        test.assertNotIn((item,w,s),seen)
        seen.add((item,w,s))
        inventory[w][item] -= q
        demand[s][item] -= q
        test.assertGreaterEqual(inventory[w][item],0)
        test.assertGreaterEqual(demand[s][item],0)
        price = state.shipping_costs_cents[w][s]
        test.assertEqual(shipment.unit_cost_cents,price)
        test.assertEqual(shipment.subtotal_cents,q*price)
        cost += q*price
        units += q
        by_item[item] += q
    for item in state.items:
        test.assertEqual(by_item[item],min(sum(row[item] for row in state.inventory.values()),
                                          sum(row[item] for row in state.demand.values())))
    test.assertEqual((plan.units_shipped,plan.total_cost_cents),(units,cost))
    test.assertEqual(plan.projected_inventory,inventory)
    test.assertEqual(plan.remaining_demand,demand)


class OptimizerTests(unittest.TestCase):
    def sample(self):
        return State.from_json((Path(__file__).resolve().parents[1]/'data/sample.json').read_text())

    def test_original_ui(self):
        state = self.sample()
        plan = compute_restock_plan(state)
        assert_plan(self,state,plan)
        self.assertEqual((plan.units_shipped,plan.total_cost_cents),(10,1400))
        self.assertEqual(plan.projected_inventory,{'warehouse_a':{'keyboards':2,'monitors':1},
                                                 'warehouse_b':{'keyboards':0,'monitors':1}})

    def test_partial_ui(self):
        state = self.sample().with_quantity('demand','store_y','monitors',6)
        plan = compute_restock_plan(state)
        assert_plan(self,state,plan)
        self.assertEqual((plan.units_shipped,plan.total_cost_cents),(12,2000))
        self.assertEqual(plan.remaining_demand,{'store_x':{'keyboards':0,'monitors':0},
                                              'store_y':{'keyboards':0,'monitors':2}})

    def test_reverse_edge_reassigns_greedy_first_choice(self):
        state = single_item_state([1,1],[1,1],[[100,200],[200,10000]])
        plan = compute_restock_plan(state)
        assert_plan(self,state,plan)
        self.assertEqual((plan.units_shipped,plan.total_cost_cents),(2,400))
        self.assertEqual({(s.warehouse_id,s.store_id,s.quantity) for s in plan.shipments},
                         {('w0','s1',1),('w1','s0',1)})

    def test_zero_exact_excess_shortage_and_ties(self):
        for stock,need,prices in [([0],[0],[[0]]),([0],[5],[[2]]),([5],[0],[[2]]),
                                 ([5],[5],[[2]]),([8],[3],[[2]]),([2],[7],[[2]]),
                                 ([1,1],[1,1],[[0,0],[0,0]]),([1,1],[1,1],[[7,7],[7,7]])]:
            with self.subTest(stock=stock,need=need,prices=prices):
                state=single_item_state(stock,need,prices)
                plan=compute_restock_plan(state)
                reference=solve_tiny(stock,need,prices)
                assert_plan(self,state,plan)
                self.assertEqual((plan.units_shipped,plan.total_cost_cents),(reference.units,reference.cost_cents))

    def test_cost_does_not_reduce_maximum_fulfillment(self):
        state=single_item_state([1],[1],[[MAX_STATE_INTEGER]])
        plan=compute_restock_plan(state)
        self.assertEqual((plan.units_shipped,plan.total_cost_cents),(1,MAX_STATE_INTEGER))

    def test_bulk_augmentation_and_exact_large_arithmetic(self):
        value=MAX_STATE_INTEGER
        matrix,cost,augmentations=_solve_item([value],[value],[[value]])
        self.assertEqual((matrix,cost,augmentations),(((value,),),value*value,1))
        state=single_item_state([value],[value],[[value]])
        assert_plan(self,state,compute_restock_plan(state))

    def test_mixed_items_cannot_substitute(self):
        state=State({'a':'A','b':'B'},{'w':'Warehouse'},{'s':'Store'},
                    {'w':{'a':5,'b':0}},{'s':{'a':0,'b':5}},{'w':{'s':0}})
        plan=compute_restock_plan(state)
        self.assertEqual((plan.units_shipped,plan.total_cost_cents),(0,0))
        assert_plan(self,state,plan)

    def test_pure_repeated_calculation_and_immutable_output(self):
        state=self.sample()
        before=state.to_dict()
        first=compute_restock_plan(state)
        self.assertEqual(first,compute_restock_plan(state))
        self.assertEqual(state.to_dict(),before)
        with self.assertRaises(FrozenInstanceError): first.units_shipped=0
        with self.assertRaises(FrozenInstanceError): first.shipments[0].quantity=0
        with self.assertRaises(TypeError): first.projected_inventory['warehouse_a']['keyboards']=99
        with self.assertRaises(TypeError): first.remaining_demand['store_x']['keyboards']=99
        edited=state.with_shipping_cost('warehouse_a','store_x',0)
        compute_restock_plan(edited)
        self.assertEqual(first,compute_restock_plan(state))

    def test_same_revision_does_not_replace_source_snapshot(self):
        state=self.sample()
        a=state.with_shipping_cost('warehouse_a','store_x',1)
        b=state.with_shipping_cost('warehouse_a','store_x',2)
        self.assertEqual(a.revision,b.revision)
        self.assertIs(compute_restock_plan(a).source_state,a)
        self.assertIs(compute_restock_plan(b).source_state,b)

    def test_raw_input_rejected(self):
        for raw in [None,{},self.sample().to_dict()]:
            with self.assertRaises(TypeError): compute_restock_plan(raw)

    def test_exhaustive_two_by_two(self):
        for capacities in product(range(3),repeat=4):
            stock,need=capacities[:2],capacities[2:]
            for prices in product(range(3),repeat=4):
                costs=[prices[:2],prices[2:]]
                state=single_item_state(stock,need,costs)
                plan=compute_restock_plan(state)
                reference=solve_tiny(stock,need,costs)
                with self.subTest(capacities=capacities,prices=prices):
                    assert_plan(self,state,plan)
                    self.assertEqual((plan.units_shipped,plan.total_cost_cents),(reference.units,reference.cost_cents))

    def test_seeded_multiple_item_rectangular_cases(self):
        rng=random.Random(4325)
        for case in range(400):
            nw,ns,ni=[rng.randint(1,3) for _ in range(3)]
            items={f'i{i}':f'Item {i}' for i in range(ni)}
            warehouses={f'w{w}':f'Warehouse {w}' for w in range(nw)}
            stores={f's{s}':f'Store {s}' for s in range(ns)}
            inventory={w:{i:rng.randrange(4) for i in items} for w in warehouses}
            demand={s:{i:rng.randrange(4) for i in items} for s in stores}
            costs=[[rng.randrange(11) for _ in stores] for _ in warehouses]
            state=State(items,warehouses,stores,inventory,demand,
                        {w:dict(zip(stores,costs[j])) for j,w in enumerate(warehouses)})
            plan=compute_restock_plan(state)
            expected_units=expected_cost=0
            for item in items:
                reference=solve_tiny([inventory[w][item] for w in warehouses],
                                     [demand[s][item] for s in stores],costs)
                expected_units+=reference.units
                expected_cost+=reference.cost_cents
            with self.subTest(case=case):
                assert_plan(self,state,plan)
                self.assertEqual((plan.units_shipped,plan.total_cost_cents),(expected_units,expected_cost))

    def test_catalog_order_and_duplicate_names(self):
        state=self.sample()
        data=state.to_dict()
        for name in ['items','warehouses','stores']:
            data[name]={key:'Same label' for key in reversed(data[name])}
        reordered=State.from_dict(data)
        plan=compute_restock_plan(reordered)
        assert_plan(self,reordered,plan)
        self.assertEqual((plan.units_shipped,plan.total_cost_cents),(10,1400))

    def test_larger_instances_price_shift_and_more_stock(self):
        rng=random.Random(54322)
        for case in range(30):
            stock=[rng.randrange(20,50) for _ in range(8)]
            need=[rng.randrange(1,10) for _ in range(7)]
            costs=[[rng.randrange(1000) for _ in need] for _ in stock]
            state=single_item_state(stock,need,costs)
            plan=compute_restock_plan(state)
            assert_plan(self,state,plan)
            shifted=compute_restock_plan(single_item_state(stock,need,[[p+17 for p in row] for row in costs]))
            self.assertEqual(shifted.total_cost_cents,plan.total_cost_cents+17*plan.units_shipped)
            extra=compute_restock_plan(single_item_state([s+10 for s in stock],need,costs))
            self.assertEqual(extra.units_shipped,plan.units_shipped)
            self.assertLessEqual(extra.total_cost_cents,plan.total_cost_cents)
            assert_plan(self,extra.source_state,extra)


if __name__=='__main__':
    unittest.main()
