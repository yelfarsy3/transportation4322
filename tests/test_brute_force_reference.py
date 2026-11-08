from dataclasses import FrozenInstanceError
from itertools import product
import random
import unittest

from brute_force_reference import SearchLimitExceeded, solve_tiny


def unit_assignment_oracle(supply, demand, costs):
    """Independent second method: assign each requested UNIT to a warehouse
    or leave it unfilled. No route-quantity recursion or reference imports.
    Intended only for at most six demanded units in this test suite.
    """
    destinations = [store for store, count in enumerate(demand) for _ in range(count)]
    best = None
    for choices in product(range(-1, len(supply)), repeat=len(destinations)):
        used = [0] * len(supply)
        units = cost = 0
        for warehouse, store in zip(choices, destinations):
            if warehouse != -1:
                used[warehouse] += 1
                units += 1
                cost += costs[warehouse][store]
        if all(count <= capacity for count, capacity in zip(used, supply)):
            key = (-units, cost)
            if best is None or key < best:
                best = key
    return -best[0], best[1]


class BruteForceReferenceTests(unittest.TestCase):
    def check_feasibility(self, result, supply, demand, costs):
        self.assertEqual(len(result.shipments), len(supply))
        for row, stock in zip(result.shipments, supply):
            self.assertEqual(len(row), len(demand))
            self.assertTrue(all(type(q) is int and q >= 0 for q in row))
            self.assertLessEqual(sum(row), stock)
        for s, need in enumerate(demand):
            self.assertLessEqual(sum(row[s] for row in result.shipments), need)
        self.assertEqual(result.units, sum(sum(row) for row in result.shipments))
        self.assertEqual(result.cost_cents, sum(q * costs[w][s]
                         for w, row in enumerate(result.shipments) for s, q in enumerate(row)))
        self.assertEqual(result.units, min(sum(supply), sum(demand)))

    def test_manual_original_and_partial_ui(self):
        costs = [[200, 500], [400, 100]]
        keyboards = solve_tiny([5, 4], [3, 4], costs)
        monitors = solve_tiny([2, 3], [1, 2], costs)
        partial = solve_tiny([2, 3], [1, 6], costs)
        self.assertEqual((keyboards.units, keyboards.cost_cents), (7, 1000))
        self.assertEqual(keyboards.shipments, ((3, 0), (0, 4)))
        self.assertEqual((monitors.units, monitors.cost_cents), (3, 400))
        self.assertEqual(monitors.shipments, ((1, 0), (0, 2)))
        self.assertEqual((partial.units, partial.cost_cents), (5, 1000))
        self.assertEqual(partial.shipments, ((1, 1), (0, 3)))
        self.assertEqual(keyboards.cost_cents + monitors.cost_cents, 1400)
        self.assertEqual(keyboards.cost_cents + partial.cost_cents, 2000)
        for result, stock, need in [(keyboards,[5,4],[3,4]),(monitors,[2,3],[1,2]),(partial,[2,3],[1,6])]:
            self.check_feasibility(result, stock, need, costs)

    def test_manual_greedy_counterexample(self):
        result = solve_tiny([1, 1], [1, 1], [[100, 200], [200, 10000]])
        self.assertEqual((result.units, result.cost_cents), (2, 400))
        self.assertEqual(result.shipments, ((0, 1), (1, 0)))

    def test_units_take_priority_over_cost(self):
        result = solve_tiny([1], [1], [[10**100]])
        self.assertEqual((result.units, result.cost_cents), (1, 10**100))

    def test_zero_exact_excess_and_shortage(self):
        for supply, demand, expected in [(0,0,(0,0)),(0,4,(0,0)),(4,0,(0,0)),
                                         (4,4,(4,28)),(5,3,(3,21)),(2,5,(2,14))]:
            with self.subTest(supply=supply,demand=demand):
                result = solve_tiny([supply],[demand],[[7]])
                self.assertEqual((result.units,result.cost_cents),expected)
                self.check_feasibility(result,[supply],[demand],[[7]])

    def test_ties_and_free_shipping(self):
        for price in [0, 7]:
            result = solve_tiny([1,1],[1,1],[[price,price],[price,price]])
            self.assertEqual((result.units,result.cost_cents),(2,2*price))
            self.check_feasibility(result,[1,1],[1,1],[[price,price],[price,price]])

    def test_exhaustive_two_by_two_domain(self):
        # ALL 3^4 capacity combinations x ALL 3^4 cost tables = 6,561 cases.
        for capacities in product(range(3), repeat=4):
            supply, demand = capacities[:2], capacities[2:]
            for prices in product(range(3), repeat=4):
                costs = (prices[:2],prices[2:])
                result = solve_tiny(supply,demand,costs)
                expected = unit_assignment_oracle(supply,demand,costs)
                with self.subTest(capacities=capacities,prices=prices):
                    self.assertEqual((result.units,result.cost_cents),expected)
                    self.check_feasibility(result,supply,demand,costs)

    def test_seeded_rectangular_instances(self):
        rng = random.Random(4324)
        for case in range(200):
            nw, ns = rng.randint(1,3), rng.randint(1,3)
            supply = [rng.randrange(3) for _ in range(nw)]
            demand = [rng.randrange(3) for _ in range(ns)]
            costs = [[rng.randrange(8) for _ in range(ns)] for _ in range(nw)]
            result = solve_tiny(supply,demand,costs)
            with self.subTest(case=case):
                self.assertEqual((result.units,result.cost_cents),unit_assignment_oracle(supply,demand,costs))
                self.check_feasibility(result,supply,demand,costs)

    def test_price_shift_scaling_and_permutation(self):
        supply,demand,costs = [2,1],[1,1],[[4,1],[2,5]]
        result = solve_tiny(supply,demand,costs)
        shifted = solve_tiny(supply,demand,[[c+9 for c in row] for row in costs])
        scaled = solve_tiny(supply,demand,[[c*7 for c in row] for row in costs])
        reordered = solve_tiny(supply[::-1],demand[::-1],[row[::-1] for row in costs[::-1]])
        self.assertEqual(shifted.cost_cents,result.cost_cents+9*result.units)
        self.assertEqual(scaled.cost_cents,result.cost_cents*7)
        self.assertEqual((reordered.units,reordered.cost_cents),(result.units,result.cost_cents))

    def test_inputs_unchanged_and_output_immutable(self):
        supply,demand,costs = [2,1],[1,2],[[3,1],[1,4]]
        result = solve_tiny(supply,demand,costs)
        self.assertEqual((supply,demand,costs),([2,1],[1,2],[[3,1],[1,4]]))
        with self.assertRaises(FrozenInstanceError): result.units = 0
        with self.assertRaises(TypeError): result.shipments[0][0] = 0

    def test_budget_never_returns_partial_optimum(self):
        supply,demand,costs = [1,1],[1,1],[[1,2],[2,100]]
        with self.assertRaises(SearchLimitExceeded): solve_tiny(supply,demand,costs,max_nodes=1)
        self.assertEqual((supply,demand,costs),([1,1],[1,1],[[1,2],[2,100]]))
        # One route with zero quantity requires root + leaf: exact budget boundary.
        self.assertEqual(solve_tiny([0],[0],[[0]],max_nodes=2).units,0)
        with self.assertRaises(SearchLimitExceeded): solve_tiny([0],[0],[[0]],max_nodes=1)
        self.assertEqual(solve_tiny(supply,demand,costs).cost_cents,4)
        with self.assertRaises(SearchLimitExceeded):
            solve_tiny([20,20,20],[20,20,20],[[1,1,1]]*3)

    def test_invalid_inputs(self):
        for supply,demand,costs in [([], [1], []),([1],[],[[]]),([1]*4,[1],[[0]]*4),
                                   ([1],[1]*4,[[0]*4]),([1],[1],[]),([1],[1],[[0,0]]),
                                   (None,[1],[[0]]),([1],[1],[None]),([21],[1],[[0]])]:
            with self.subTest(supply=supply,demand=demand,costs=costs), self.assertRaises(ValueError):
                solve_tiny(supply,demand,costs)
        for value in [-1,True,False,1.0,'1',None,float('nan'),float('inf')]:
            for supply,demand,costs in [([value],[1],[[0]]),([1],[value],[[0]]),([1],[1],[[value]])]:
                with self.assertRaises(ValueError): solve_tiny(supply,demand,costs)
        for budget in [0,-1,True,1.0,None]:
            with self.assertRaises(ValueError): solve_tiny([1],[1],[[0]],max_nodes=budget)


if __name__ == '__main__':
    unittest.main()
