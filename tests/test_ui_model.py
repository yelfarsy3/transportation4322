from itertools import product
import unittest
from data_model import MAX_STATE_INTEGER, ValidationError
from ui_model import money, quantity, price, rows_for, table_from_rows
from test_operations import sample_state

class UIConversionTests(unittest.TestCase):
    def test_exact_money_round_trip(self):
        for cents in list(range(10001)) + [2**53+1, MAX_STATE_INTEGER]:
            self.assertEqual(price(money(cents)), cents)
        for text, expected in [('1',100), ('1.2',120), ('0.01',1), ('000.00',0)]:
            self.assertEqual(price(text),expected)

    def test_invalid_money_and_counts(self):
        for text in ['', '-1', '+1', ' 1', '1 ', '1e3', 'NaN', 'Infinity', '١', '1,000', True, None, 2.0, '9'*301]:
            for parse in (price,quantity):
                with self.subTest(text=text,parse=parse), self.assertRaises(ValidationError): parse(text)
        for text in ['1.001', '$1', '.50', '1.', str(MAX_STATE_INTEGER)]:
            with self.assertRaises(ValidationError): price(text)
        for text in ['1.0','0.01']:
            with self.assertRaises(ValidationError): quantity(text)
        self.assertEqual(quantity(str(MAX_STATE_INTEGER)),MAX_STATE_INTEGER)

    def test_tables_roundtrip_and_shape_rejection(self):
        state=sample_state()
        for name, rowcat, colcat, costs in [('inventory',state.warehouses,state.items,False),
                ('demand',state.stores,state.items,False),('shipping_costs_cents',state.warehouses,state.stores,True)]:
            rows=rows_for(getattr(state,name),rowcat,colcat,costs=costs)
            self.assertEqual(table_from_rows(rows,rowcat,colcat,costs=costs),getattr(state,name))
            for bad in [rows[:-1],rows[::-1],rows+[rows[0]],None,[{} for row in rows]]:
                with self.assertRaises(ValidationError): table_from_rows(bad,rowcat,colcat,costs=costs)

    def test_catalog_ids_cannot_collide_with_ui_columns(self):
        rowcat={'v0':'Same','Location':'Same'}; colcat={'Location':'Same','v0':'Same'}
        for a,b,c,d in product(range(3),repeat=4):
            table={'v0':{'Location':a,'v0':b},'Location':{'Location':c,'v0':d}}
            self.assertEqual(table_from_rows(rows_for(table,rowcat,colcat),rowcat,colcat),table)

    def test_display_labels_remain_unique_when_names_look_like_ids(self):
        from ui_model import labels
        catalog={'a':'Same','b':'Same','c':'Same [a]'}
        self.assertEqual(len(set(labels(catalog).values())),3)
