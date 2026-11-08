from itertools import product
import unittest

from brute_force_reference import solve_tiny
from optimizer import compute_restock_plan, _add_edge, _shortest_path_dijkstra
from test_optimizer import single_item_state, assert_plan


class PotentialsTests(unittest.TestCase):
    def test_both_methods_exhaustive_against_reference(self):
        for capacities in product(range(3),repeat=4):
            stock,need=capacities[:2],capacities[2:]
            for prices in product(range(3),repeat=4):
                costs=[prices[:2],prices[2:]]
                state=single_item_state(stock,need,costs)
                reference=solve_tiny(stock,need,costs)
                for method in ['bellman_ford','dijkstra']:
                    plan=compute_restock_plan(state,method=method)
                    with self.subTest(capacities=capacities,prices=prices,method=method):
                        assert_plan(self,state,plan)
                        self.assertEqual((plan.units_shipped,plan.total_cost_cents),
                                         (reference.units,reference.cost_cents))

    def test_distances_finish_before_potential_update(self):
        # Vertex 1 can be the sink, settled at distance 1; vertex 2's tentative
        # distance 10 is later improved via vertex 3. Early exit is incorrect.
        graph=[[] for _ in range(5)]
        _add_edge(graph,0,1,1,1)
        _add_edge(graph,0,2,1,10)
        _add_edge(graph,0,3,1,2)
        _add_edge(graph,3,2,1,1)
        potentials=[0]*5
        distances,_=_shortest_path_dijkstra(graph,0,potentials)
        self.assertEqual(distances,[0,1,3,2,None])
        self.assertEqual(potentials,[0,1,3,2,0])
        for v,edges in enumerate(graph):
            for edge in edges:
                if edge.capacity>0 and distances[v] is not None:
                    self.assertGreaterEqual(edge.cost+potentials[v]-potentials[edge.to],0)

    def test_reverse_path_after_first_augmentation(self):
        state=single_item_state([1,1],[1,1],[[1,2],[2,100]])
        for method in ['bellman_ford','dijkstra']:
            plan=compute_restock_plan(state,method=method)
            self.assertEqual((plan.units_shipped,plan.total_cost_cents),(2,4))
            assert_plan(self,state,plan)

    def test_zero_stock_unreachable_vertices_and_zero_prices(self):
        for costs in [[[0,0],[0,0],[0,0]],[[100,99],[2,3],[7,1]]]:
            state=single_item_state([0,2,2],[0,3],costs)
            answers=[]
            for method in ['bellman_ford','dijkstra']:
                plan=compute_restock_plan(state,method=method)
                assert_plan(self,state,plan)
                answers.append((plan.units_shipped,plan.total_cost_cents))
            self.assertEqual(answers[0],answers[1])

    def test_invalid_method_rejected_even_when_no_flow(self):
        for value in ['greedy','',None,[],{},0]:
            with self.subTest(value=value),self.assertRaises(ValueError):
                compute_restock_plan(single_item_state([0],[0],[[0]]),method=value)

    def test_negative_reduced_cost_guard(self):
        graph=[[],[]]
        _add_edge(graph,0,1,1,1)
        with self.assertRaises(RuntimeError):
            _shortest_path_dijkstra(graph,0,[0,2])


if __name__=='__main__':
    unittest.main()
