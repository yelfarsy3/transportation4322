# Stage 4: an independent reference for tiny inputs

Source: approved plan Stage 4; general project instructions pp. 1–2 require
incremental checks and permit AI-created testing tools. This checker is ordinary
Python enumeration, with no linear programming or external optimization library.

## What was built

`tests/brute_force_reference.py` accepts one item's stock per warehouse, demand
per store, and shipping-price matrix in cents. It returns maximum shipped units,
minimum cost for that quantity, and a feasible shipment matrix.

It never imports the production data model, availability calculation, or future
optimizer. It never edits input lists or writes state. It belongs only in tests.
The efficient production algorithm is still Stage 5 and has not been implemented.

The objective is ordered: maximize units first, then minimize cost. For example,
shipping one available/requested unit at a high price still beats shipping zero.
Fairness is not a constraint. Different plans with the same units and cost are
equally correct; tests must not demand a particular allocation in a tied case.

## How exhaustive enumeration works

Process routes in a fixed order. For each route, try every integer quantity from
zero through the smaller of remaining warehouse stock and remaining store demand.
Temporarily subtract that quantity, try the next route, then restore the quantities
before trying the next alternative. At the last route, compare the complete plan.

The comparison key is `(-units, cost)`: the smallest key prioritizes the largest
shipment count, then the smallest cost. Python tuple comparisons implement this
ordering directly; no guessed penalty constant is needed.

Invariant: before each recursive call, remaining stock and demand equal their
original values minus shipments already assigned. They never become negative.
Restoring quantities after each branch ensures later branches start with the same
resources. Every feasible shipment matrix has one sequence of choices in this
tree, so a completed search visits every feasible allocation and selects the best.

If there are E = warehouses × stores routes and every route quantity is at most Q,
the number of leaves is at most (Q+1)^E. A simple upper bound on runtime is
O(E × (Q+1)^E), including copying an allocation when recording a better answer.
Auxiliary space is O(E + warehouses + stores): current matrix, best matrix, input
copies, remaining quantities, and a recursion stack of depth E. This is exponential
and intentionally unsuitable for the real Restock button.

## Practical bounds

The testing tool accepts 1–3 warehouses, 1–3 stores, and quantity cells from 0 to
20. Prices are nonnegative integer cents; zero prices and tied optima are valid.
The default search budget is 250,000 visited nodes. Some accepted-size instances
still exceed this budget. In that case it raises SearchLimitExceeded and returns
no plan: an incomplete search must never be presented as a proven optimum.

These are testing-tool limits, not limits imposed on the eventual production
optimizer. Inputs remain untouched even when a search hits the budget.

## Hand-worked checks

| Example | Units | Cost |
|---|---:|---:|
| Original keyboards | 7 | 1000 cents |
| Original monitors | 3 | 400 cents |
| Original combined | 10 | 1400 cents ($14) |
| Partial monitors (Y needs 6) | 5 | 1000 cents |
| Partial combined | 12 | 2000 cents ($20) |
| Greedy counterexample | 2 | 400 cents ($4) |

Why these costs are minimal:

- Keyboards: X needs 3, each costing at least $2; Y needs 4, each costing at
  least $1. A→X=3 and B→Y=4 achieve the $10 lower bound.
- Original monitors: the analogous lower bound is 1×$2 + 2×$1 = $4,
  attained by A→X=1 and B→Y=2.
- Partial monitors: maximum fulfillment requires using all 2 at A and all 3 at
  B. X can accept only 1, so at least 1 of A's units must cost $5 to Y; A's
  other unit costs at least $2. B's 3 units cost at least $1 each. The $10 bound
  is attained by A→X=1, A→Y=1 and B→Y=3. Y remains short by 2 monitors.
- Greedy example: with stocks/demands [1,1] and costs [[100,200],[200,10000]],
  the only two full-shipment matchings cost 10100 and 400 cents. The crossed
  routes are cheaper. Zero shipments are cheaper still, but fail the first
  objective of maximizing fulfillment.

## Independent checks actually run

The normal test suite compares all 6,561 two-by-two instances with quantity cells
and cost cells from 0–2 against a second method that assigns individual demanded
units to warehouses or leaves them unmet. It also checks 200 seeded rectangular
instances, manual examples, bounds, ties, zero inputs and immutability.

The separate audit compares all 65,536 two-by-two instances with quantity and
cost cells from 0–3 against a third method: generate flat matrices and filter them
by capacity constraints. These domains overlap; do not add their counts and
claim all are distinct cases. Neither finite domain covers all possible inputs.

The audit additionally changes the checker in memory to introduce three defects:
minimize cost before maximizing units, omit a maximum route quantity, and use the
wrong store price. The existing manual tests detect each. No real source file is
modified by those checks. This is evidence that tests challenge the objective and
allocation logic instead of merely checking that the function runs.

## Your verification gate

Before running, explain the two greedy-example matchings, and why the partial
monitor example needs one $5 shipment. Then run from the project folder:

```sh
.venv/bin/python -B -m unittest discover -s tests -v
.venv/bin/python -B tests/audit_reference.py
.venv/bin/python -B - <<'PY'
import sys
sys.path.insert(0, 'tests')
from brute_force_reference import solve_tiny
print(solve_tiny([1, 1], [1, 1], [[100, 200], [200, 10000]]))
print(solve_tiny([2, 3], [1, 6], [[200, 500], [400, 100]]))
PY
```

Expected: 43 tests pass; audit reports 65,536 matches and three detected defects.
The two printed results have (units, cost_cents) equal to (2,400) and (5,1000).
Also explain why a tied optimum may have a different shipment matrix and why a
budget-exhausted run must return no claimed optimum.

Student Stage 4 verification: pending. Record personal observations accurately.
After this gate, Stage 5 implements the production minimum-cost-flow algorithm
and uses this reference to check its results on tiny instances.
