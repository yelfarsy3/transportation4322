from dataclasses import FrozenInstanceError
import json
from pathlib import Path
import random
import unittest

from data_model import State, ValidationError

SAMPLE = Path(__file__).resolve().parents[1] / "data/sample.json"


class DataModelTests(unittest.TestCase):
    def setUp(self):
        self.text = SAMPLE.read_text()
        self.raw = json.loads(self.text)
        self.state = State.from_json(self.text)

    def test_sample_matches_ui(self):
        self.assertEqual(dict(self.state.inventory['warehouse_a']), {'keyboards': 5, 'monitors': 2})
        self.assertEqual(dict(self.state.inventory['warehouse_b']), {'keyboards': 4, 'monitors': 3})
        self.assertEqual(dict(self.state.demand['store_x']), {'keyboards': 3, 'monitors': 1})
        self.assertEqual(dict(self.state.demand['store_y']), {'keyboards': 4, 'monitors': 2})
        self.assertEqual(self.state.to_dict()['shipping_costs_cents'], {
            'warehouse_a': {'store_x': 200, 'store_y': 500},
            'warehouse_b': {'store_x': 400, 'store_y': 100}})
        # Hand totals from the PDF, not an optimizer or production totals function.
        for item, stock, demand in [('keyboards', 9, 7), ('monitors', 5, 3)]:
            self.assertEqual(sum(row[item] for row in self.state.inventory.values()), stock)
            self.assertEqual(sum(row[item] for row in self.state.demand.values()), demand)

    def test_quantity_edits_are_isolated(self):
        updated = self.state.with_quantity('inventory', 'warehouse_a', 'keyboards', 3, 'add')
        self.assertEqual(updated.inventory['warehouse_a']['keyboards'], 8)
        self.assertEqual(updated.inventory['warehouse_a']['monitors'], 2)
        self.assertEqual(updated.revision, 1)
        self.assertEqual(self.state.to_dict(), self.raw)
        updated = updated.with_quantity('inventory', 'warehouse_a', 'keyboards', 8, 'remove')
        self.assertEqual(updated.inventory['warehouse_a']['keyboards'], 0)
        self.assertEqual(updated.revision, 2)

    def test_partial_ui_input_retains_other_cells(self):
        updated = self.state.with_quantity('demand', 'store_y', 'monitors', 6)
        expected = json.loads(self.text)
        expected['demand']['store_y']['monitors'] = 6
        expected['revision'] = 1
        self.assertEqual(updated.to_dict(), expected)

    def test_bad_edits_do_not_change_state(self):
        for args in [
            ('inventory','warehouse_a','keyboards',6,'remove'),
            ('inventory','store_x','keyboards',1,'set'),
            ('demand','store_x','unknown',1,'set'),
            ('inventory','warehouse_a','keyboards',1,'multiply'),
            ('unknown','warehouse_a','keyboards',1,'set'),
        ]:
            with self.subTest(args=args), self.assertRaises(ValidationError):
                self.state.with_quantity(*args)
        self.assertEqual(self.state.to_dict(), self.raw)

    def test_invalid_numeric_values(self):
        for value in [-1, 1.0, 1.5, True, False, '3', None, float('nan'), float('inf')]:
            for table, row, column in [
                ('inventory','warehouse_a','keyboards'),
                ('demand','store_x','monitors'),
                ('shipping_costs_cents','warehouse_b','store_y'),
            ]:
                with self.subTest(value=value, table=table), self.assertRaises(ValidationError):
                    data = self.state.to_dict()
                    data[table][row][column] = value
                    State.from_dict(data)
            with self.subTest(edit=value), self.assertRaises(ValidationError):
                self.state.with_quantity('inventory','warehouse_a','keyboards',value)

    def test_missing_and_extra_matrix_references(self):
        for table in ['inventory','demand','shipping_costs_cents']:
            for change in ['missing_row','extra_row','missing_cell','extra_cell','bad_row']:
                data = self.state.to_dict()
                matrix = data[table]
                first = next(iter(matrix))
                if change == 'missing_row': del matrix[first]
                elif change == 'extra_row': matrix['unknown'] = dict(matrix[first])
                elif change == 'missing_cell': matrix[first].pop(next(iter(matrix[first])))
                elif change == 'extra_cell': matrix[first]['unknown'] = 0
                else: matrix[first] = []
                with self.subTest(table=table, change=change), self.assertRaises(ValidationError):
                    State.from_dict(data)

    def test_bad_catalogs(self):
        for name in ['items','warehouses','stores']:
            for value in [{}, [], None, {'': 'Name'}, {'id': ' '}, {1:'Name'}, {' id':'Name'}]:
                data = self.state.to_dict()
                data[name] = value
                with self.subTest(name=name,value=value), self.assertRaises(ValidationError):
                    State.from_dict(data)

    def test_schema_and_revision(self):
        for field, values in [('schema_version',[0,2,True,1.0]), ('revision',[-1,True,0.0])]:
            for value in values:
                data = self.state.to_dict()
                data[field] = value
                with self.subTest(field=field,value=value), self.assertRaises(ValidationError):
                    State.from_dict(data)

    def test_json_errors_and_duplicate_keys(self):
        for text in ['{', '[]', 'null', '{}', '{"items":{},"items":{}}',
                     self.text.replace('"keyboards": 5', '"keyboards": 5, "keyboards": 8')]:
            with self.subTest(text=text[:40]), self.assertRaises(ValidationError):
                State.from_json(text)
        for change in ['missing','extra']:
            data = self.state.to_dict()
            if change == 'missing': del data['revision']
            else: data['unexpected'] = 1
            with self.assertRaises(ValidationError): State.from_dict(data)

    def test_snapshot_protects_against_aliasing(self):
        state = State.from_dict(self.raw)
        self.raw['inventory']['warehouse_a']['keyboards'] = 100
        output = state.to_dict()
        output['demand']['store_x']['monitors'] = 100
        self.assertEqual(state.inventory['warehouse_a']['keyboards'], 5)
        self.assertEqual(state.demand['store_x']['monitors'], 1)
        with self.assertRaises(TypeError): state.inventory['warehouse_a']['keyboards'] = 9
        with self.assertRaises(TypeError): state.items['keyboards'] = 'Changed'
        with self.assertRaises(FrozenInstanceError): state.revision = 2

    def test_roundtrip(self):
        self.assertEqual(State.from_json(json.dumps(self.state.to_dict())), self.state)

    def test_names_are_labels_not_references(self):
        self.raw['warehouses']['warehouse_a'] = 'Renamed warehouse'
        state = State.from_dict(self.raw)
        self.assertEqual(state.inventory['warehouse_a']['keyboards'], 5)
        self.assertEqual(state.shipping_costs_cents['warehouse_a']['store_x'], 200)

    def test_prices_and_noops(self):
        updated = self.state.with_shipping_cost('warehouse_a','store_x',0)
        self.assertEqual(updated.shipping_costs_cents['warehouse_a']['store_x'], 0)
        self.assertEqual(updated.revision, 1)
        self.assertEqual(self.state.shipping_costs_cents['warehouse_a']['store_x'], 200)
        self.assertIs(self.state.with_shipping_cost('warehouse_a','store_x',200), self.state)
        self.assertIs(self.state.with_quantity('demand','store_x','monitors',1), self.state)
        for w,s,c in [('bad','store_x',1),('warehouse_a','bad',1),('warehouse_a','store_x',2.5)]:
            with self.assertRaises(ValidationError): self.state.with_shipping_cost(w,s,c)

    def test_singleton_zero_and_large_integer(self):
        state = State(items={'i':'Item'},warehouses={'w':'Warehouse'},stores={'s':'Store'},
                      inventory={'w':{'i':0}},demand={'s':{'i':0}},shipping_costs_cents={'w':{'s':0}})
        big = 10**100
        updated = state.with_quantity('inventory','w','i',big).with_shipping_cost('w','s',big)
        self.assertEqual(updated.inventory['w']['i'], big)
        self.assertEqual(updated.shipping_costs_cents['w']['s'] * big, 10**200)

    def test_seeded_edit_sequences_against_plain_dictionary(self):
        rng = random.Random(4322)
        state = self.state
        expected = self.state.to_dict()
        for _ in range(250):
            table = rng.choice(['inventory','demand'])
            location = rng.choice(list(expected[table]))
            item = rng.choice(list(expected['items']))
            value = rng.randrange(50)
            old = expected[table][location][item]
            state = state.with_quantity(table,location,item,value)
            expected[table][location][item] = value
            expected['revision'] += (old != value)
            self.assertEqual(state.to_dict(), expected)


if __name__ == '__main__':
    unittest.main()
