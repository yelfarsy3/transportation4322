"""Cross-check both methods, certify larger flows, inject defects, and benchmark."""
import io
from itertools import product
from pathlib import Path
import platform
import random
import statistics
import sys
from time import perf_counter
import types
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from data_model import State
from optimizer import compute_restock_plan
from brute_force_reference import solve_tiny
from audit_optimizer import assert_no_negative_cycle
from test_optimizer import single_item_state, assert_plan
import test_optimizer


def exhaustive_both():
    matrices=list(product(range(4),repeat=4))
    checker=unittest.TestCase()
    count=0
    for a,b,x,y in product(range(4),repeat=4):
        feasible=[q for q in matrices if q[0]+q[1]<=a and q[2]+q[3]<=b
                  and q[0]+q[2]<=x and q[1]+q[3]<=y]
        units=max(map(sum,feasible))
        full=[q for q in feasible if sum(q)==units]
        for prices in product(range(4),repeat=4):
            cost=min(sum(qi*ci for qi,ci in zip(q,prices)) for q in full)
            state=single_item_state([a,b],[x,y],[prices[:2],prices[2:]])
            for method in ['bellman_ford','dijkstra']:
                plan=compute_restock_plan(state,method=method)
                assert_plan(checker,state,plan)
                assert (plan.units_shipped,plan.total_cost_cents)==(units,cost)
            count+=1
    print(f'PASS: both methods match flat enumeration on all {count} 2x2 cases, quantities/costs 0..3')


def random_state(rng,nw,ns,ni,quantity_max,cost_max):
    items={f'i{i}':f'Item {i}' for i in range(ni)}
    warehouses={f'w{w}':f'Warehouse {w}' for w in range(nw)}
    stores={f's{s}':f'Store {s}' for s in range(ns)}
    return State(items,warehouses,stores,
                 {w:{i:rng.randrange(quantity_max+1) for i in items} for w in warehouses},
                 {s:{i:rng.randrange(quantity_max+1) for i in items} for s in stores},
                 {w:{s:rng.randrange(cost_max+1) for s in stores} for w in warehouses})


def random_checks():
    rng=random.Random(4326)
    checker=unittest.TestCase()
    for case in range(300):
        state=random_state(rng,rng.randint(1,3),rng.randint(1,3),rng.randint(1,3),3,20)
        costs=[list(state.shipping_costs_cents[w].values()) for w in state.warehouses]
        expected_units=expected_cost=0
        for item in state.items:
            ref=solve_tiny([state.inventory[w][item] for w in state.warehouses],
                           [state.demand[s][item] for s in state.stores],costs)
            expected_units+=ref.units
            expected_cost+=ref.cost_cents
        before=state.to_dict()
        for method in ['bellman_ford','dijkstra']:
            plan=compute_restock_plan(state,method=method)
            assert_plan(checker,state,plan)
            assert (plan.units_shipped,plan.total_cost_cents)==(expected_units,expected_cost)
        assert state.to_dict()==before
    print('PASS: 300 seeded multi-item cases, both methods versus Stage 4 enumeration')
    for case in range(150):
        state=random_state(rng,rng.randint(1,12),rng.randint(1,12),rng.randint(1,3),100,10000)
        objectives=[]
        for method in ['bellman_ford','dijkstra']:
            plan=compute_restock_plan(state,method=method)
            assert_plan(checker,state,plan)
            assert_no_negative_cycle(state,plan)
            objectives.append((plan.units_shipped,plan.total_cost_cents))
        assert objectives[0]==objectives[1]
    print('PASS: 150 larger multi-item cases; identical objectives and independent residual-cycle certificates')


def mutation_checks():
    source=(Path(__file__).resolve().parents[1]/'optimizer.py').read_text()
    variants=[('potential updates omitted','potentials[vertex] += value','potentials[vertex] += 0'),
              ('potential signs reversed','edge.cost + potentials[vertex] - potentials[edge.to]',
               'edge.cost - potentials[vertex] + potentials[edge.to]'),
              ('reduced distance charged as currency','cost += amount * path_cost',
               'cost += amount * distance[sink]')]
    original=test_optimizer.compute_restock_plan
    try:
        for index,(label,old,new) in enumerate(variants):
            assert source.count(old)==1
            name=f'_potential_mutant_{index}'
            module=types.ModuleType(name)
            sys.modules[name]=module
            try:
                exec(compile(source.replace(old,new),name,'exec'),module.__dict__)
                test_optimizer.compute_restock_plan=module.compute_restock_plan
                suite=unittest.TestSuite(test_optimizer.OptimizerTests(n) for n in [
                    'test_original_ui','test_partial_ui','test_reverse_edge_reassigns_greedy_first_choice'])
                result=unittest.TextTestRunner(stream=io.StringIO()).run(suite)
                assert not result.wasSuccessful(),f'Missed defect: {label}'
                print(f'PASS: rejected {label} ({len(result.failures)} assertion failures, {len(result.errors)} errors)')
            finally:
                del sys.modules[name]
    finally:
        test_optimizer.compute_restock_plan=original


def benchmark():
    rng=random.Random(64322)
    checker=unittest.TestCase()
    print(f'BENCHMARK: Python {platform.python_version()}, {platform.machine()}, {platform.system()}; median of 3 runs')
    print('warehouses,stores,items,bellman_ford_seconds,dijkstra_seconds,BF/Dijkstra')
    for nw,ns,ni in [(4,4,2),(12,12,3),(30,30,3),(60,60,3)]:
        state=random_state(rng,nw,ns,ni,100,10000)
        durations={method:[] for method in ['bellman_ford','dijkstra']}
        objectives={}
        # Warm both methods, then alternate order to reduce ordering bias.
        for method in durations: compute_restock_plan(state,method=method)
        for repeat in range(3):
            methods=list(durations)
            if repeat%2: methods.reverse()
            for method in methods:
                start=perf_counter()
                plan=compute_restock_plan(state,method=method)
                durations[method].append(perf_counter()-start)
                assert_plan(checker,state,plan)
                objectives[method]=(plan.units_shipped,plan.total_cost_cents)
        assert objectives['bellman_ford']==objectives['dijkstra']
        bf,dj=[statistics.median(durations[m]) for m in ['bellman_ford','dijkstra']]
        print(f'{nw},{ns},{ni},{bf:.6f},{dj:.6f},{bf/dj:.2f}')


if __name__=='__main__':
    exhaustive_both()
    random_checks()
    mutation_checks()
    benchmark()
