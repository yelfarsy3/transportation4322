# Stage 2: understand and verify before continuing

The problem at this stage is representing facts accurately, not selecting routes.
For example, A has 5 keyboards and 2 monitors. Adding 3 keyboards must produce
8 keyboards and 2 monitors. A dictionary keyed by stable IDs makes that distinction
explicit. A label change does not change the key used by inventory and prices.

A minimal baseline would be mutable dictionaries. That makes it easy for preview
code to change real stock accidentally. Our improvement is a validated snapshot:
copy the dictionaries, check every entry, and expose read-only mappings. Edits
create another snapshot. This deliberately trades a full-state copy for a simple
and inspectable safety rule.

Invariant: every public State has exactly the catalog-defined rows and columns,
and every quantity/cost is a nonnegative integer. Construction validates each
cell; an edit builds a new State through the same validation path. Therefore valid
construction plus valid edits preserves that invariant, and failure cannot partly
change the old State. This does not establish any optimizer property.

Please predict these answers before running the code yourself:

1. A has 5 keyboards. Add 3, then remove 8. What remains? What happens to monitors?
2. Why reject `True`, even though Python treats it as an integer subtype?
3. Why reject a missing shipping price instead of treating it as zero?
4. If Y's monitor demand becomes 6, what are total monitor stock and demand?
5. Why must a preview avoid changing the input State?

Run from the project folder:

```sh
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python - <<'PY'
from pathlib import Path
from data_model import State, ValidationError
s = State.from_json(Path('data/sample.json').read_text())
t = s.with_quantity('inventory', 'warehouse_a', 'keyboards', 3, 'add')
print('Before:', dict(s.inventory['warehouse_a']))
print('After:', dict(t.inventory['warehouse_a']))
try:
    t.with_quantity('inventory', 'warehouse_a', 'keyboards', 9, 'remove')
except ValidationError as error:
    print('Rejected:', error)
print('After failed edit:', dict(t.inventory['warehouse_a']))
PY
```

Expected: before 5 keyboards/2 monitors, after 8 keyboards/2 monitors; removing
9 is rejected, leaving 8/2. Record what you actually observe and explain why.

Student verification: Done. No understanding or personal test completion
has been inferred from the agent's test results.
