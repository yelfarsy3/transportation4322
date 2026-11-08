"""Regression cases reproduced during the read-only Stage 3 audit."""
import json
from pathlib import Path
import unittest

from availability import ItemAvailability, calculate_availability
from data_model import MAX_STATE_INTEGER, State, ValidationError


class ValidationBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.text = (Path(__file__).resolve().parents[1] / 'data/sample.json').read_text()
        self.state = State.from_json(self.text)

    def test_malformed_ids_have_consistent_errors(self):
        for invalid in [[], {}, None, True, 1, 1.0, '', 'unknown']:
            calls = [
                lambda: self.state.with_quantity('inventory', invalid, 'keyboards', 1),
                lambda: self.state.with_quantity('inventory', 'warehouse_a', invalid, 1),
                lambda: self.state.with_shipping_cost(invalid, 'store_x', 1),
                lambda: self.state.with_shipping_cost('warehouse_a', invalid, 1),
            ]
            for call in calls:
                with self.subTest(invalid=invalid), self.assertRaises(ValidationError):
                    call()
        self.assertEqual(self.state, State.from_json(self.text))

    def test_malformed_json_errors_are_normalized(self):
        for text in [b'\xff', bytearray(b'\xff'), '[', None, 42,
                     '[' * 2000 + '0' + ']' * 2000,
                     self.text.replace('"keyboards": 5', '"keyboards": ' + '9' * 5000)]:
            with self.subTest(kind=type(text)), self.assertRaises(ValidationError):
                State.from_json(text)

    def test_supported_limit_roundtrips(self):
        data = self.state.to_dict()
        data['revision'] = MAX_STATE_INTEGER
        for table in ['inventory', 'demand', 'shipping_costs_cents']:
            for row in data[table].values():
                for col in row:
                    row[col] = MAX_STATE_INTEGER
        state = State.from_dict(data)
        self.assertEqual(State.from_json(json.dumps(state.to_dict())), state)
        self.assertEqual(calculate_availability(state)['keyboards'].supply, 2 * MAX_STATE_INTEGER)

    def test_all_stored_numeric_fields_reject_above_limit(self):
        for value in [MAX_STATE_INTEGER + 1, 10**5000]:
            for table in ['inventory', 'demand', 'shipping_costs_cents']:
                data = self.state.to_dict()
                first_row = next(iter(data[table].values()))
                first_row[next(iter(first_row))] = value
                with self.subTest(table=table), self.assertRaises(ValidationError):
                    State.from_dict(data)
            data = self.state.to_dict()
            data['revision'] = value
            with self.assertRaises(ValidationError): State.from_dict(data)

    def test_limit_edits_and_revision_overflow_are_atomic(self):
        top = self.state.with_quantity('inventory', 'warehouse_a', 'keyboards', MAX_STATE_INTEGER)
        before = top.to_dict()
        for quantity, operation in [(1, 'add'), (MAX_STATE_INTEGER + 1, 'set')]:
            with self.assertRaises(ValidationError):
                top.with_quantity('inventory', 'warehouse_a', 'keyboards', quantity, operation)
        self.assertEqual(top.to_dict(), before)
        with self.assertRaises(ValidationError):
            top.with_shipping_cost('warehouse_a', 'store_x', MAX_STATE_INTEGER + 1)
        data = top.to_dict()
        data['revision'] = MAX_STATE_INTEGER
        capped = State.from_dict(data)
        with self.assertRaises(ValidationError):
            capped.with_shipping_cost('warehouse_a', 'store_x', 201)
        self.assertEqual(capped.to_dict(), data)
        self.assertIs(capped.with_shipping_cost('warehouse_a', 'store_x', 200), capped)

    def test_report_construction_rejects_invalid_counts(self):
        for value in [-1, True, False, 0.0, 2.5, '2', None, [], {}, float('nan'), float('inf')]:
            for supply, demand in [(value, 2), (2, value)]:
                with self.subTest(value=value), self.assertRaises(ValidationError):
                    ItemAvailability(supply, demand)
        self.assertEqual(ItemAvailability(0, 2).shortage, 2)
        self.assertEqual(ItemAvailability(2, 0).shippable, 0)


if __name__ == '__main__':
    unittest.main()
