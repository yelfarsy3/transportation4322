from dataclasses import FrozenInstanceError
from pathlib import Path
import random
import unittest

from availability import calculate_availability
from data_model import State


def make_state(stock, demand, costs=None):
    """Test inputs are location rows, each containing quantities by item."""
    items = {f'i{i}': f'Item {i}' for i in range(len(stock[0]))}
    warehouses = {f'w{w}': f'Warehouse {w}' for w in range(len(stock))}
    stores = {f's{s}': f'Store {s}' for s in range(len(demand))}
    return State(
        items=items, warehouses=warehouses, stores=stores,
        inventory={w: dict(zip(items, row)) for w, row in zip(warehouses, stock)},
        demand={s: dict(zip(items, row)) for s, row in zip(stores, demand)},
        shipping_costs_cents={w: {s: costs[wi][si] if costs else 0
                                 for si, s in enumerate(stores)}
                             for wi, w in enumerate(warehouses)},
    )


class AvailabilityTests(unittest.TestCase):
    def sample(self):
        path = Path(__file__).resolve().parents[1] / 'data/sample.json'
        return State.from_json(path.read_text())

    def assert_counts(self, actual, expected):
        self.assertEqual(
            (actual.supply, actual.demand, actual.shippable, actual.shortage), expected
        )

    def test_original_ui_totals(self):
        result = calculate_availability(self.sample())
        self.assert_counts(result['keyboards'], (9, 7, 7, 0))
        self.assert_counts(result['monitors'], (5, 3, 3, 0))
        self.assertEqual(sum(item.shippable for item in result.values()), 10)

    def test_partial_ui_does_not_substitute_items(self):
        state = self.sample().with_quantity('demand', 'store_y', 'monitors', 6)
        result = calculate_availability(state)
        self.assert_counts(result['keyboards'], (9, 7, 7, 0))
        self.assert_counts(result['monitors'], (5, 7, 5, 2))
        self.assertEqual(sum(item.supply for item in result.values()), 14)
        self.assertEqual(sum(item.demand for item in result.values()), 14)
        self.assertEqual(sum(item.shippable for item in result.values()), 12)

    def test_exact_excess_shortage_and_zero_boundaries(self):
        cases = [
            (4, 4, (4, 4, 4, 0)), (9, 4, (9, 4, 4, 0)),
            (2, 7, (2, 7, 2, 5)), (9, 0, (9, 0, 0, 0)),
            (0, 7, (0, 7, 0, 7)), (0, 0, (0, 0, 0, 0)),
        ]
        for stock, demand, expected in cases:
            with self.subTest(stock=stock, demand=demand):
                self.assert_counts(calculate_availability(make_state([[stock]], [[demand]]))['i0'], expected)

    def test_multiple_locations_and_mixed_items(self):
        state = make_state([[0, 3, 0], [5, 0, 0], [2, 1, 0]], [[1, 0, 2], [2, 6, 1]])
        result = calculate_availability(state)
        for item, expected in {'i0': (7, 3, 3, 0), 'i1': (4, 6, 4, 2), 'i2': (0, 3, 0, 3)}.items():
            self.assert_counts(result[item], expected)

    def test_prices_do_not_limit_availability(self):
        state = self.sample()
        expensive = state.with_shipping_cost('warehouse_a', 'store_x', 10**100)
        free = state.with_shipping_cost('warehouse_a', 'store_x', 0)
        self.assertEqual(calculate_availability(state), calculate_availability(expensive))
        self.assertEqual(calculate_availability(state), calculate_availability(free))

    def test_large_counts_without_per_unit_iteration(self):
        big = 10**100
        result = calculate_availability(make_state([[big], [big]], [[3 * big]]))
        self.assert_counts(result['i0'], (2 * big, 3 * big, 2 * big, big))

    def test_no_mutation_and_independent_snapshots(self):
        state = self.sample()
        before = state.to_dict()
        report = calculate_availability(state)
        self.assertEqual(state.to_dict(), before)
        updated = state.with_quantity('demand', 'store_y', 'monitors', 6)
        self.assertEqual(calculate_availability(updated)['monitors'].shortage, 2)
        self.assertEqual(report['monitors'].shortage, 0)
        with self.assertRaises(TypeError): report['monitors'] = report['keyboards']
        with self.assertRaises(FrozenInstanceError): report['monitors'].supply = 100

    def test_raw_input_requires_validation_first(self):
        for invalid in [None, {}, self.sample().to_dict()]:
            with self.subTest(invalid=type(invalid)), self.assertRaises(TypeError):
                calculate_availability(invalid)

    def test_catalog_order_does_not_mix_items(self):
        state = self.sample()
        data = state.to_dict()
        data['items'] = dict(reversed(list(data['items'].items())))
        data['warehouses'] = dict(reversed(list(data['warehouses'].items())))
        self.assertEqual(calculate_availability(state), calculate_availability(State.from_dict(data)))

    def test_seeded_cases_against_unit_matching(self):
        # Independent tiny-count reference: match physical unit tokens one by one.
        # This checks counts only, not routes or cost; Stage 4 will check those.
        rng = random.Random(4323)
        for case in range(200):
            ni, nw, ns = (rng.randint(1, 4) for _ in range(3))
            stock = [[rng.randrange(6) for _ in range(ni)] for _ in range(nw)]
            demand = [[rng.randrange(6) for _ in range(ni)] for _ in range(ns)]
            result = calculate_availability(make_state(stock, demand))
            for i in range(ni):
                stock_tokens = [None for row in stock for _ in range(row[i])]
                demand_tokens = [None for row in demand for _ in range(row[i])]
                initial_supply, initial_demand = len(stock_tokens), len(demand_tokens)
                matched = 0
                while stock_tokens and demand_tokens:
                    stock_tokens.pop()
                    demand_tokens.pop()
                    matched += 1
                with self.subTest(case=case, item=i):
                    self.assert_counts(result[f'i{i}'],
                                       (initial_supply, initial_demand, matched, len(demand_tokens)))


if __name__ == '__main__':
    unittest.main()
