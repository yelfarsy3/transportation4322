# Stage 3: availability before route selection

Source: approved plan Stage 3; assignment p. 1 specifies separate quantities for
each item and a price for every warehouse/store pair. The chosen model has no
shared route capacities or item substitution.

## Contract and example

`calculate_availability(state)` accepts a validated State and returns an immutable
mapping from item ID to supply, demand, shippable units and shortage. It does not
change inventory, demand or revision. It does not decide which store receives
scarce units, choose routes, calculate cost, or save anything.

For the partial UI input (Store Y needs 6 monitors):

| Item | Supply | Demand | Shippable | Shortage |
|---|---:|---:|---:|---:|
| Keyboards | 9 | 7 | 7 | 0 |
| Monitors | 5 | 7 | 5 | 2 |
| Total | 14 | 14 | 12 | 2 |

Do not take `min(total stock, total demand)` across different items. Extra
keyboards cannot satisfy monitor demand. Also, this stage cannot say which store
will be short; that depends on route costs and the later optimizer.

## Why the formula is correct

A simple baseline is to pair available units with requested units one at a time.
That works for counts but wastes time when quantities are large. Instead, sum
stock and demand once per item, then use `min(supply, demand)`.

No plan can ship more than the stock or more than the demand. Conversely, while
both remain positive, at least one warehouse has stock and one store has demand.
The complete route table means that warehouse can supply that store. Pairing can
continue until one side runs out, reaching the smaller total. The remaining
demand is `demand - shippable`. This argument would need revision if routes were
missing or shared capacity constraints were introduced.

During summation, the running total equals the quantities in the rows visited.
After every row has been visited, it equals the full supply or demand for that
item. Results satisfy `0 <= shippable <= supply`, `shippable <= demand`, and
`shippable + shortage == demand`.

Time: O(n1 * (n2 + n3)); auxiliary space: O(n1) for the report. This counts
integer arithmetic operations; very large integers also have bit-operation cost.
There is no loop over individual units in the production function.

## Predict, run, explain

Before running, calculate by hand: original sample; Y changed to 6 monitors;
zero demand; zero stock; exact stock of 4 against demand of 4. Explain why a
price change cannot alter these counts under the chosen model.

From the project folder, run:

```sh
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python - <<'PY'
from pathlib import Path
from data_model import State
from availability import calculate_availability
s = State.from_json(Path('data/sample.json').read_text())
partial = s.with_quantity('demand', 'store_y', 'monitors', 6)
for label, state in [('Original', s), ('Partial', partial)]:
    print(label)
    for item, counts in calculate_availability(state).items():
        print(item, counts.supply, counts.demand, counts.shippable, counts.shortage)
print('Original Y monitor demand:', s.demand['store_y']['monitors'])
PY
```

Expected original rows: keyboards `9 7 7 0`, monitors `5 3 3 0`.
Expected partial rows: keyboards `9 7 7 0`, monitors `5 7 5 2`.
The final original demand is still `2`. The tests include zero-demand, zero-stock,
exact-supply and mixed-item cases as well as 200 seeded tiny random inputs checked
by unit matching. Unit matching verifies counts only, not optimal route costs.

Stage 3 student verification: done. Record your actual observations separately
from the agent's test evidence. Stage 4 is the tiny exhaustive route/cost checker.
