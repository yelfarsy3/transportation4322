"""Ready-made scenarios, the independent optimality certificate, and scenario loading."""
import json
import os
import random
import tempfile
import unittest
from itertools import product
from pathlib import Path
from unittest.mock import patch
from streamlit.testing.v1 import AppTest

from brute_force_reference import solve_tiny
from data_model import State
from operations import RestockSession
from optimizer import compute_restock_plan, trace_restock_plan
from scenarios import list_scenarios
from storage import JsonStore, SCENARIO_DIR, StorageConflict, StorageError
from teaching import certify, cheapest_first
from test_operations import sample_state

APP = Path(__file__).resolve().parents[1] / 'app.py'
SCENARIOS = list_scenarios()


def per_item(state, item):
    W, S = list(state.warehouses), list(state.stores)
    return ([state.inventory[w][item] for w in W], [state.demand[s][item] for s in S],
            [[state.shipping_costs_cents[w][s] for s in S] for w in W])


def brute_force_fits(state):
    return (len(state.warehouses) <= 3 and len(state.stores) <= 3 and
            all(v <= 20 for table in (state.inventory, state.demand) for row in table.values() for v in row.values()))


def reverse_steps(state):
    nw = len(state.warehouses)
    return sum(1 for record in trace_restock_plan(state) for path in record['paths']
               for u, _ in zip(path['vertices'][1:-1], path['vertices'][2:-1]) if u >= nw)


class ScenarioFileTests(unittest.TestCase):
    def test_about_ten_complete_scenarios(self):
        self.assertGreaterEqual(len(SCENARIOS), 10)
        for sc in SCENARIOS:
            with self.subTest(sc.slug):
                st = sc.state
                self.assertTrue(st.items and st.warehouses and st.stores)
                self.assertEqual(set(st.inventory), set(st.warehouses))
                self.assertEqual(set(st.demand), set(st.stores))
                self.assertTrue(all(set(row) == set(st.stores) for row in st.shipping_costs_cents.values()))
                self.assertTrue(any(v for row in st.inventory.values() for v in row.values()))
                self.assertTrue(any(v for row in st.demand.values() for v in row.values()))

    def test_stored_expectations_match_plan(self):
        for sc in SCENARIOS:
            plan = compute_restock_plan(sc.state)
            self.assertEqual((plan.units_shipped, plan.total_cost_cents),
                             (sc.expected_units, sc.expected_cost_cents), sc.slug)

    def test_brute_force_agrees_where_enumerable(self):
        checked = 0
        for sc in SCENARIOS:
            if not brute_force_fits(sc.state):
                continue
            checked += 1
            units = cost = 0
            for item in sc.state.items:
                result = solve_tiny(*per_item(sc.state, item))
                units += result.units; cost += result.cost_cents
            self.assertEqual((units, cost), (sc.expected_units, sc.expected_cost_cents), sc.slug)
        self.assertGreaterEqual(checked, 9)

    def test_both_search_methods_agree_and_certificate_holds(self):
        for sc in SCENARIOS:
            fast = compute_restock_plan(sc.state)
            slow = compute_restock_plan(sc.state, method='bellman_ford')
            self.assertEqual((fast.units_shipped, fast.total_cost_cents),
                             (slow.units_shipped, slow.total_cost_cents), sc.slug)
            self.assertTrue(all(c.optimal for c in certify(sc.state, fast)), sc.slug)
            self.assertTrue(all(c.optimal for c in certify(sc.state, slow)), sc.slug)

    def test_reassignment_claims_are_checked(self):
        tagged = [sc for sc in SCENARIOS if 'reassignment' in sc.tags]
        self.assertGreaterEqual(len(tagged), 2)
        for sc in tagged:
            self.assertGreater(reverse_steps(sc.state), 0, sc.slug)
        chained = next(sc for sc in SCENARIOS if sc.slug == '03-chained-reassignment')
        nw = len(chained.state.warehouses)
        self.assertTrue(any(sum(1 for u, _ in zip(p['vertices'][1:-1], p['vertices'][2:-1]) if u >= nw) >= 2
                            for r in trace_restock_plan(chained.state) for p in r['paths']))

    def test_greedy_trap_is_caught_by_certificate(self):
        trap = next(sc for sc in SCENARIOS if sc.slug == '02-greedy-trap')
        allocation, cost = cheapest_first(trap.state)
        self.assertEqual((cost, trap.expected_cost_cents), (4400, 1600))
        cycle = next(c for c in certify(trap.state, allocation=allocation) if c.cycle)
        self.assertEqual(cycle.cycle_cost_cents, -700)


class CertificateTests(unittest.TestCase):
    def test_certificate_matches_brute_force_on_every_max_allocation(self):
        """For random tiny networks, enumerate maximum allocations: the certificate
        must accept exactly those whose cost equals the brute-force optimum."""
        rng = random.Random(4322)
        for _ in range(120):
            nw, ns = rng.randint(1, 2), rng.randint(1, 3)
            W, S = [f'w{i}' for i in range(nw)], [f's{i}' for i in range(ns)]
            stock = [rng.randint(0, 3) for _ in W]; need = [rng.randint(0, 3) for _ in S]
            costs = [[rng.randint(0, 5) for _ in S] for _ in W]
            state = State({'i': 'I'}, {w: w for w in W}, {s: s for s in S},
                          {w: {'i': stock[k]} for k, w in enumerate(W)}, {s: {'i': need[k]} for k, s in enumerate(S)},
                          {w: {s: costs[a][b] for b, s in enumerate(S)} for a, w in enumerate(W)})
            best = solve_tiny(stock, need, costs)
            cells = [(a, b) for a in range(nw) for b in range(ns)]
            for values in product(range(4), repeat=len(cells)):
                x = dict(zip(cells, values))
                if any(sum(x[(a, b)] for b in range(ns)) > stock[a] for a in range(nw)) or \
                   any(sum(x[(a, b)] for a in range(nw)) > need[b] for b in range(ns)) or \
                   sum(values) != best.units:
                    continue
                cost = sum(x[c] * costs[c[0]][c[1]] for c in cells)
                cert = certify(state, allocation={'i': {(W[a], S[b]): q for (a, b), q in x.items() if q}})[0]
                self.assertEqual(cert.optimal, cost == best.cost_cents, (stock, need, costs, x))
                if cert.cycle:
                    self.assertLess(cert.cycle_cost_cents, 0)

    def test_short_allocation_is_not_optimal(self):
        state = sample_state()
        self.assertFalse(all(c.optimal for c in certify(state, allocation={})))


class LoadScenarioTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory(); self.addCleanup(folder.cleanup)
        self.folder = Path(folder.name)
        self.store = JsonStore(self.folder / 'state.json'); self.store.initialize(sample_state())

    def test_load_replaces_ids_advances_revision_and_clears_preview(self):
        files = {p: p.read_bytes() for p in SCENARIO_DIR.glob('*.json')}
        session = RestockSession.open(self.store); session.preview()
        trap = next(sc for sc in SCENARIOS if sc.slug == '02-greedy-trap')
        session.load_scenario(trap.state)
        saved = self.store.load()
        self.assertEqual((saved.revision, dict(saved.items)), (1, {'chairs': 'Chairs'}))
        self.assertIsNone(session.pending_preview)
        self.assertEqual(files, {p: p.read_bytes() for p in SCENARIO_DIR.glob('*.json')})

    def test_load_respects_stale_save_protection(self):
        session = RestockSession.open(self.store)
        old = self.store.load(); self.store.commit(old, old.with_quantity('inventory', 'warehouse_a', 'keyboards', 9))
        with self.assertRaises(StorageConflict):
            session.load_scenario(SCENARIOS[1].state)

    def test_regular_commit_still_refuses_catalog_change(self):
        old = self.store.load(); data = SCENARIOS[1].state.to_dict(); data['revision'] = 1
        with self.assertRaises(StorageError):
            self.store.commit(old, State.from_dict(data))

    def test_working_file_cannot_be_a_scenario_file(self):
        with self.assertRaises(StorageError):
            JsonStore(SCENARIO_DIR / '01-baseline.json')


class ScenarioAppTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory(); self.addCleanup(folder.cleanup)
        self.store = JsonStore(Path(folder.name) / 'state.json'); self.store.initialize(sample_state())
        env = patch.dict(os.environ, {'TRANSPORTATION_STATE_PATH': str(self.store.path)})
        env.start(); self.addCleanup(env.stop)
        self.app = AppTest.from_file(APP).run(timeout=20)

    def click(self, key):
        self.app.button(key=key).click().run(timeout=20)
        self.assertEqual(len(self.app.exception), 0, str(self.app.exception))

    def test_load_needs_confirmation_then_reset_restores_sample(self):
        self.app.selectbox(key='scenario_choice').select('02-greedy-trap').run(timeout=20)
        self.click('load_scenario')
        self.assertEqual(self.store.load(), sample_state())
        self.click('cancel_load'); self.assertEqual(self.store.load(), sample_state())
        self.click('load_scenario'); self.click('confirm_load')
        self.assertEqual(set(self.store.load().items), {'chairs'})
        self.assertIn('Greedy trap', self.app.success[0].value)
        self.click('preview')
        self.assertIn('$16.00', ' '.join(x.value for x in self.app.markdown))
        self.assertIn('44.00', ' '.join(x.value for x in self.app.caption))
        self.app.checkbox[0].check(); self.click('reset')
        saved = self.store.load()
        self.assertEqual((saved.items, saved.inventory), (sample_state().items, sample_state().inventory))
        self.assertEqual(saved.revision, 2)


if __name__ == '__main__':
    unittest.main()
