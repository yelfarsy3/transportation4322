"""One small, hand-traceable case that proves the planner does more than
"ship the cheapest route first".

Reassignment cascade (data/scenarios/11-reassignment-cascade.json), one item:

    stock  North 3, Central 2, South 2      need  Store A 3, Store B 3, Store C 1
    $/unit          A    B    C
           North    3   10    9
           Central  1    4    5      <- Central→A ($1) is the cheapest route
           South    2    6    8

Successive shortest paths (⟵ = reassignment, an earlier allocation undone):

    1  Central→A                                   2 units  $1
    2  South→A                                     1 unit   $2
    3  South→A ⟵Central  Central→B                 1 unit   2-1+4 = $5
    4  North→A ⟵Central  Central→B                 1 unit   3-1+4 = $6
    5  North→A ⟵South    South→B                   1 unit   3-2+6 = $7
    6  North→A ⟵South    South→B ⟵Central Central→C 1 unit  3-2+6-4+5 = $8

Optimum $30: North→A 3, Central→B 1, Central→C 1, South→B 2. The $1 route
ends up unused. Cheapest-first fills Central→A first and pays $39.
"""
import itertools
import unittest
from pathlib import Path

from brute_force_reference import solve_tiny
from optimizer import _solve_item, compute_restock_plan, trace_restock_plan
from scenarios import load_scenario_file
from storage import SCENARIO_DIR
from teaching import certify, cheapest_first

W = ['North', 'Central', 'South']
S = ['A', 'B', 'C']
STOCK = [3, 2, 2]
NEED = [3, 3, 1]
COSTS = [[3, 10, 9], [1, 4, 5], [2, 6, 8]]          # dollars, as in the docstring
CENTS = [[c * 100 for c in row] for row in COSTS]

# (route steps, units, per-unit cost in cents); ('<', w, s) is a reassignment on w→s.
EXPECTED_PATHS = [
    ([('>', 'Central', 'A')], 2, 100),
    ([('>', 'South', 'A')], 1, 200),
    ([('>', 'South', 'A'), ('<', 'Central', 'A'), ('>', 'Central', 'B')], 1, 500),
    ([('>', 'North', 'A'), ('<', 'Central', 'A'), ('>', 'Central', 'B')], 1, 600),
    ([('>', 'North', 'A'), ('<', 'South', 'A'), ('>', 'South', 'B')], 1, 700),
    ([('>', 'North', 'A'), ('<', 'South', 'A'), ('>', 'South', 'B'),
      ('<', 'Central', 'B'), ('>', 'Central', 'C')], 1, 800),
]
# Allocation (rows North, Central, South; columns A, B, C) after each path.
EXPECTED_FLOWS = [
    [[0, 0, 0], [2, 0, 0], [0, 0, 0]],
    [[0, 0, 0], [2, 0, 0], [1, 0, 0]],
    [[0, 0, 0], [1, 1, 0], [2, 0, 0]],
    [[1, 0, 0], [0, 2, 0], [2, 0, 0]],
    [[2, 0, 0], [0, 2, 0], [1, 1, 0]],
    [[3, 0, 0], [0, 1, 1], [0, 2, 0]],
]
OPTIMUM = [[3, 0, 0], [0, 1, 1], [0, 2, 0]]


def readable(trace):
    nw = len(W)
    out = []
    for path in trace:
        middle = path['vertices'][1:-1]
        steps = [('>', W[u], S[v - nw]) if u < nw else ('<', W[v], S[u - nw])
                 for u, v in zip(middle, middle[1:])]
        out.append((steps, path['amount'], path['path_cost']))
    return out


def every_full_allocation():
    """Every way to ship all 7 units (row sums = stock, column sums = need)."""
    cells = [(w, s) for w in range(3) for s in range(3)]
    for values in itertools.product(*(range(min(STOCK[w], NEED[s]) + 1) for w, s in cells)):
        x = [[0] * 3 for _ in range(3)]
        for (w, s), q in zip(cells, values):
            x[w][s] = q
        if [sum(r) for r in x] == STOCK and [sum(x[w][s] for w in range(3)) for s in range(3)] == NEED:
            yield x


def cost(x):
    return sum(x[w][s] * CENTS[w][s] for w in range(3) for s in range(3))


class ReassignmentCascadeTests(unittest.TestCase):
    def setUp(self):
        self.trace = []
        self.allocation, self.cost, self.paths = _solve_item(STOCK, NEED, CENTS, trace=self.trace)

    def test_exact_augmenting_paths(self):
        self.assertEqual(readable(self.trace), EXPECTED_PATHS)
        self.assertEqual(sum(1 for steps, _, _ in EXPECTED_PATHS for kind, _, _ in steps if kind == '<'), 5)

    def test_flow_table_after_every_path(self):
        flow = [[0] * 3 for _ in range(3)]
        for (steps, units, _), expected in zip(EXPECTED_PATHS, EXPECTED_FLOWS):
            for kind, w, s in steps:
                flow[W.index(w)][S.index(s)] += units if kind == '>' else -units
                self.assertGreaterEqual(flow[W.index(w)][S.index(s)], 0)
            self.assertEqual(flow, expected)

    def test_path_costs_rise_and_sum_to_total(self):
        per_unit = [c for _, _, c in EXPECTED_PATHS]
        self.assertEqual(per_unit, sorted(per_unit))      # successive shortest paths never get cheaper
        self.assertEqual(sum(u * c for _, u, c in EXPECTED_PATHS), 3000)
        self.assertEqual((self.cost, [list(r) for r in self.allocation]), (3000, OPTIMUM))

    def test_bellman_ford_takes_the_same_paths(self):
        baseline = []
        _solve_item(STOCK, NEED, CENTS, method='bellman_ford', trace=baseline)
        self.assertEqual(readable(baseline), readable(self.trace))

    def test_each_cheapest_path_is_unique(self):
        """At every step, list every simple residual path from spare stock to unmet
        demand; the recorded path is the only cheapest one, so ties cannot change it."""
        before = [[[0] * 3 for _ in range(3)]] + EXPECTED_FLOWS[:-1]
        for flow, (_, _, chosen) in zip(before, EXPECTED_PATHS):
            left = [STOCK[w] - sum(flow[w]) for w in range(3)]
            got = [sum(flow[w][s] for w in range(3)) for s in range(3)]
            found = []

            def walk(w, used_w, used_s, total):
                for s in range(3):
                    if s in used_s:
                        continue
                    here = total + CENTS[w][s]
                    if got[s] < NEED[s]:
                        found.append(here)
                    for w2 in range(3):
                        if w2 not in used_w and flow[w2][s] > 0:
                            walk(w2, used_w | {w2}, used_s | {s}, here - CENTS[w2][s])

            for w in range(3):
                if left[w]:
                    walk(w, {w}, set(), 0)
            self.assertEqual(min(found), chosen)
            self.assertEqual(found.count(chosen), 1)

    def test_exhaustive_optimum_is_unique_and_avoids_cheapest_route(self):
        plans = list(every_full_allocation())
        best = min(cost(x) for x in plans)
        self.assertEqual(best, 3000)
        self.assertEqual([x for x in plans if cost(x) == best], [OPTIMUM])
        uses_cheapest = [x for x in plans if x[1][0] > 0]          # Central→A at $1
        self.assertTrue(uses_cheapest)
        self.assertGreater(min(cost(x) for x in uses_cheapest), best)
        self.assertEqual(solve_tiny(STOCK, NEED, CENTS).cost_cents, best)

    def test_cheapest_first_pays_39_and_certificate_finds_the_fix(self):
        scenario = load_scenario_file(SCENARIO_DIR / '11-reassignment-cascade.json')
        state = scenario.state
        allocation, greedy_cost = cheapest_first(state)
        self.assertEqual(greedy_cost, 3900)
        self.assertEqual(allocation['bikes'][('central', 'a')], 2)       # greedy keeps the $1 route
        broken = next(c for c in certify(state, allocation=allocation) if c.cycle)
        self.assertLess(broken.cycle_cost_cents, 0)
        plan = compute_restock_plan(state)
        self.assertTrue(all(c.optimal for c in certify(state, plan)))
        self.assertEqual((plan.units_shipped, plan.total_cost_cents),
                         (scenario.expected_units, scenario.expected_cost_cents))
        self.assertEqual(len(trace_restock_plan(state)[0]['paths']), 6)
        self.assertNotIn(('bikes', 'central', 'a'),
                         {(s.item_id, s.warehouse_id, s.store_id) for s in plan.shipments})


if __name__ == '__main__':
    unittest.main()
