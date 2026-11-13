"""Ready-made teaching scenarios in data/scenarios/*.json (read-only).

Each file: title, purpose, tags, expected {units, cost_cents}, state. Expected
totals are checked by tests against an independent brute-force reference and an
optimality certificate; they are documentation, not inputs to the optimizer.
"""
import json
from dataclasses import dataclass

from data_model import State, ValidationError
from storage import SCENARIO_DIR


@dataclass(frozen=True)
class Scenario:
    slug: str
    title: str
    purpose: str
    tags: tuple
    expected_units: int
    expected_cost_cents: int
    state: State


def load_scenario_file(path):
    try:
        doc = json.loads(path.read_text(encoding='utf-8'))
        expected = doc['expected']
        if not all(isinstance(doc[k], str) and doc[k] for k in ('title', 'purpose')):
            raise ValidationError('Scenario title and purpose must be text')
        for key in ('units', 'cost_cents'):
            if type(expected[key]) is not int or expected[key] < 0:
                raise ValidationError(f'Scenario expected {key} must be a whole number')
        return Scenario(path.stem, doc['title'], doc['purpose'], tuple(doc.get('tags', ())),
                        expected['units'], expected['cost_cents'], State.from_dict(doc['state']))
    except (OSError, ValueError, KeyError, TypeError) as error:
        raise ValidationError(f'Scenario {path.name} is invalid: {error}') from error


def list_scenarios(folder=SCENARIO_DIR):
    return tuple(load_scenario_file(path) for path in sorted(folder.glob('*.json')))
