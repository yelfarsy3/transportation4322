"""Exact text conversion at the UI boundary; no floats or optimization here."""
import re
import json
from collections import Counter
from data_model import MAX_STATE_INTEGER, ValidationError


def money(cents):
    return f'{cents // 100}.{cents % 100:02d}'


def quantity(text):
    if not isinstance(text, str) or not re.fullmatch(r'[0-9]{1,300}', text):
        raise ValidationError('Enter a whole number of 0 or more (at most 300 digits).')
    return int(text)


def price(text):
    if not isinstance(text, str) or not re.fullmatch(r'[0-9]{1,300}(?:\.[0-9]{1,2})?', text):
        raise ValidationError('Enter dollars with at most two decimal places, without a $ sign.')
    whole, _, fraction = text.partition('.')
    cents = int(whole) * 100 + int(fraction.ljust(2, '0'))
    if cents > MAX_STATE_INTEGER:
        raise ValidationError('Price exceeds the supported integer limit.')
    return cents


def labels(catalog):
    counts = Counter(catalog.values())
    result = {key: name if counts[name] == 1 else f'{name} [{key}]'
              for key, name in catalog.items()}
    # A literal name can itself look like a generated label. JSON pairs make
    # the fallback unambiguous even for IDs/names containing brackets.
    if len(set(result.values())) != len(result):
        return {key: json.dumps([name, key], ensure_ascii=False) for key, name in catalog.items()}
    return result


def rows_for(table, row_catalog, column_catalog, *, costs=False):
    # Synthetic column keys avoid collisions with user-provided catalog IDs.
    names = labels(row_catalog)
    render = money if costs else str
    return [{'Location': names[row_id], **{f'v{n}': render(table[row_id][col_id])
            for n, col_id in enumerate(column_catalog)}} for row_id in row_catalog]


def table_from_rows(rows, row_catalog, column_catalog, *, costs=False):
    names = labels(row_catalog)
    keys = {'Location'} | {f'v{n}' for n in range(len(column_catalog))}
    if not isinstance(rows, list) or len(rows) != len(row_catalog):
        raise ValidationError('Table dimensions changed. Discard edits and try again.')
    result = {}
    for row, row_id in zip(rows, row_catalog):
        if not isinstance(row, dict) or set(row) != keys or row['Location'] != names[row_id]:
            raise ValidationError('Table locations changed. Discard edits and try again.')
        result[row_id] = {}
        for n, col_id in enumerate(column_catalog):
            try:
                result[row_id][col_id] = (price if costs else quantity)(row[f'v{n}'])
            except ValidationError as error:
                raise ValidationError(f'{names[row_id]} / {labels(column_catalog)[col_id]}: {error}') from error
    return result
