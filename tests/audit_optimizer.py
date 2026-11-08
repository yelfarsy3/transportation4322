"""Independent Stage 5 audit: finite exhaustive comparisons and residual cycles."""
import io
from itertools import product
from pathlib import Path
import random
import sys
import types
import unittest

# Allow the documented direct invocation from any working directory.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from optimizer import compute_restock_plan
from test_optimizer import single_item_state, assert_plan
import test_optimizer


def assert_no_negative_cycle(state, plan):
    """Independent optimality certificate via Floyd–Warshall, not Bellman–Ford.
    A feasible maximum flow is minimum-cost iff its residual graph has no
    negative-cost cycle. Start from returned shipments, not solver internals.
    """
    warehouses,stores=list(state.warehouses),list(state.stores)
    nw,ns=len(warehouses),len(stores)
    source,sink=nw+ns,nw+ns+1
    size=nw+ns+2
    for item in state.items:
        flow={(s.warehouse_id,s.store_id):s.quantity for s in plan.shipments if s.item_id==item}
        distance=[[None]*size for _ in range(size)]
        for v in range(size): distance[v][v]=0
        def edge(a,b,capacity,cost):
            if capacity>0 and (distance[a][b] is None or cost<distance[a][b]):
                distance[a][b]=cost
        for wi,w in enumerate(warehouses):
            sent=sum(flow.get((w,s),0) for s in stores)
            edge(source,wi,state.inventory[w][item]-sent,0)
            edge(wi,source,sent,0)
            for si,s in enumerate(stores):
                q=flow.get((w,s),0)
                capacity=min(state.inventory[w][item],state.demand[s][item])
                cost=state.shipping_costs_cents[w][s]
                edge(wi,nw+si,capacity-q,cost)
                edge(nw+si,wi,q,-cost)
        for si,s in enumerate(stores):
            received=sum(flow.get((w,s),0) for w in warehouses)
            edge(nw+si,sink,state.demand[s][item]-received,0)
            edge(sink,nw+si,received,0)
        for k in range(size):
            for i in range(size):
                if distance[i][k] is None: continue
                for j in range(size):
                    if distance[k][j] is None: continue
                    candidate=distance[i][k]+distance[k][j]
                    if distance[i][j] is None or candidate<distance[i][j]:
                        distance[i][j]=candidate
        assert all(distance[v][v]>=0 for v in range(size)), 'Negative residual cost cycle found'


def exhaustive_check():
    matrices=list(product(range(4),repeat=4))
    check=unittest.TestCase()
    count=0
    for a,b,x,y in product(range(4),repeat=4):
        feasible=[q for q in matrices if q[0]+q[1]<=a and q[2]+q[3]<=b
                  and q[0]+q[2]<=x and q[1]+q[3]<=y]
        maximum=max(map(sum,feasible))
        full=[q for q in feasible if sum(q)==maximum]
        for prices in product(range(4),repeat=4):
            expected=min(sum(qi*ci for qi,ci in zip(q,prices)) for q in full)
            state=single_item_state([a,b],[x,y],[prices[:2],prices[2:]])
            plan=compute_restock_plan(state)
            assert (plan.units_shipped,plan.total_cost_cents)==(maximum,expected)
            assert_plan(check,state,plan)
            count+=1
    print(f'PASS: {count} exhaustive 2x2 cases, quantities/costs 0..3, versus flat matrix enumeration')


def cycle_certificate_check():
    rng=random.Random(54325)
    check=unittest.TestCase()
    for _ in range(200):
        nw,ns=rng.randint(1,10),rng.randint(1,10)
        state=single_item_state([rng.randrange(100) for _ in range(nw)],
                                [rng.randrange(100) for _ in range(ns)],
                                [[rng.randrange(10000) for _ in range(ns)] for _ in range(nw)])
        plan=compute_restock_plan(state)
        assert_plan(check,state,plan)
        assert_no_negative_cycle(state,plan)
    # Ensure the certificate rejects a known feasible but nonoptimal flow.
    state=single_item_state([1,1],[1,1],[[100,200],[200,10000]])
    fake=types.SimpleNamespace(shipments=(
        types.SimpleNamespace(item_id='i',warehouse_id='w0',store_id='s0',quantity=1),
        types.SimpleNamespace(item_id='i',warehouse_id='w1',store_id='s1',quantity=1)))
    try: assert_no_negative_cycle(state,fake)
    except AssertionError: pass
    else: raise AssertionError('Certificate failed to reject the greedy allocation')
    print('PASS: 200 larger instances, independent Floyd–Warshall residual-cycle certificate; rejected greedy plan')


def mutation_checks():
    source=(Path(__file__).resolve().parents[1]/'optimizer.py').read_text()
    variants=[('reverse capacity disabled', 'graph[edge.to][edge.reverse].capacity += amount',
               'graph[edge.to][edge.reverse].capacity += 0'),
              ('reverse cost sign wrong','0, -cost)','0, cost)'),
              ('cost used from wrong store','costs[w][s])','costs[w][0])')]
    original=test_optimizer.compute_restock_plan
    try:
        for index,(label,old,new) in enumerate(variants):
            assert source.count(old)==1, (label,source.count(old))
            name=f'_optimizer_mutation_{index}'
            module=types.ModuleType(name)
            sys.modules[name]=module
            try:
                exec(compile(source.replace(old,new),name,'exec'),module.__dict__)
                test_optimizer.compute_restock_plan=module.compute_restock_plan
                suite=unittest.TestSuite(test_optimizer.OptimizerTests(n) for n in [
                    'test_original_ui','test_partial_ui','test_reverse_edge_reassigns_greedy_first_choice',
                    'test_zero_exact_excess_shortage_and_ties'])
                result=unittest.TextTestRunner(stream=io.StringIO()).run(suite)
                assert not result.wasSuccessful(),f'Missed defect: {label}'
                print(f'PASS: detected {label} ({len(result.failures)} assertion failures, {len(result.errors)} errors)')
            finally:
                del sys.modules[name]
    finally:
        test_optimizer.compute_restock_plan=original


if __name__=='__main__':
    exhaustive_check()
    cycle_certificate_check()
    mutation_checks()
