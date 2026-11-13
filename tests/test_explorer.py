"""Explorer replay: trace fidelity, payload limits, and the preview button."""
import os
import random
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from streamlit.testing.v1 import AppTest

import explorer
from data_model import State
from optimizer import _solve_item, compute_restock_plan, trace_restock_plan
from storage import JsonStore
from test_operations import sample_state

APP = Path(__file__).resolve().parents[1] / 'app.py'


def random_state(rng, nw, ns, ni):
    W = [f'w{i}' for i in range(nw)]; S = [f's{i}' for i in range(ns)]; I = [f'i{i}' for i in range(ni)]
    return State.from_dict({'schema_version': 1, 'revision': 0,
        'items': {i: i.upper() for i in I}, 'warehouses': {w: w.upper() for w in W},
        'stores': {s: s.upper() for s in S},
        'inventory': {w: {i: rng.randint(0, 6) for i in I} for w in W},
        'demand': {s: {i: rng.randint(0, 6) for i in I} for s in S},
        'shipping_costs_cents': {w: {s: rng.randint(0, 900) for s in S} for w in W}})


def replay(state, record):
    """Apply recorded paths the way the page does; return flow, units, cost."""
    nw, ns = len(state.warehouses), len(state.stores)
    rates = [[state.shipping_costs_cents[w][s] for s in state.stores] for w in state.warehouses]
    flow = [[0] * ns for _ in range(nw)]; units = cost = 0
    for path in record['paths']:
        middle = path['vertices'][1:-1]
        expected = 0
        for u, v in zip(middle, middle[1:]):
            if u < nw:
                flow[u][v - nw] += path['amount']; expected += rates[u][v - nw]
            else:
                flow[v][u - nw] -= path['amount']; expected -= rates[v][u - nw]
                assert flow[v][u - nw] >= 0, 'reassignment undid more than was allocated'
        assert expected == path['path_cost']
        units += path['amount']; cost += path['amount'] * path['path_cost']
    return flow, units, cost


class TraceTests(unittest.TestCase):
    def test_trace_replays_to_exact_plan_on_random_networks(self):
        rng = random.Random(4322)
        saw_reassignment = False
        for _ in range(300):
            state = random_state(rng, rng.randint(1, 4), rng.randint(1, 4), rng.randint(1, 2))
            plan = compute_restock_plan(state)
            units = cost = 0
            for record in trace_restock_plan(state):
                flow, u, c = replay(state, record)
                self.assertEqual(tuple(map(tuple, flow)), record['allocation'])
                units += u; cost += c
                saw_reassignment |= any(v >= len(state.warehouses) and w < len(state.warehouses)
                    for p in record['paths'] for v, w in zip(p['vertices'][1:-2], p['vertices'][2:-1]))
            self.assertEqual((units, cost), (plan.units_shipped, plan.total_cost_cents))
        self.assertTrue(saw_reassignment, 'random cases should exercise reverse edges')

    def test_tracing_does_not_change_solver_result(self):
        stock, need, costs = [5, 4], [3, 4], [[200, 500], [400, 100]]
        self.assertEqual(_solve_item(stock, need, costs), _solve_item(stock, need, costs, trace=[]))

    def test_payload_uses_strings_and_labels(self):
        payload, reason = explorer.build_payload(sample_state())
        self.assertIsNone(reason)
        self.assertEqual(payload['warehouses'], ['Warehouse A', 'Warehouse B'])
        self.assertTrue(all(isinstance(x, str) for x in payload['items'][0]['stock']))
        html = explorer.render_html(payload)
        self.assertNotIn('__PAYLOAD__', html)

    def test_large_network_is_declined_with_reason(self):
        state = random_state(random.Random(1), explorer.MAX_LOCATIONS + 1, 2, 1)
        payload, reason = explorer.build_payload(state)
        self.assertIsNone(payload); self.assertIn('up to', reason)

    def test_script_breakout_is_escaped(self):
        data = sample_state().to_dict(); data['items']['keyboards'] = '</script><b>x'
        html = explorer.render_html(explorer.build_payload(State.from_dict(data))[0])
        self.assertNotIn('</script><b>', html)


class ExploreButtonTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory(); self.addCleanup(folder.cleanup)
        self.store = JsonStore(Path(folder.name) / 'state.json'); self.store.initialize(sample_state())
        env = patch.dict(os.environ, {'TRANSPORTATION_STATE_PATH': str(self.store.path)})
        env.start(); self.addCleanup(env.stop)
        self.app = AppTest.from_file(APP).run(timeout=20)

    def click(self, key):
        self.app.button(key=key).click().run(timeout=20)
        self.assertEqual(len(self.app.exception), 0, str(self.app.exception))

    def test_explore_toggles_without_touching_saved_data(self):
        original = self.store.path.read_bytes()
        self.click('preview')
        self.assertEqual(self.app.button(key='explore').label, 'Explore algorithm')
        self.click('explore')
        self.assertEqual(self.app.button(key='explore').label, 'Show final plan')
        self.click('explore')
        self.assertEqual(self.app.button(key='explore').label, 'Explore algorithm')
        self.click('explore'); self.click('cancel'); self.click('preview')
        self.assertEqual(self.app.button(key='explore').label, 'Explore algorithm')
        self.assertEqual(self.store.path.read_bytes(), original)
        self.click('confirm')
        self.assertEqual(len([b for b in self.app.button if b.key == 'explore']), 0)


if __name__ == '__main__':
    unittest.main()
