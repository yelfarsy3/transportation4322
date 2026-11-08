# Stage 5: minimum-cost maximum-flow with Bellman–Ford

The approved plan's Stage 5 is implemented in `optimizer.py`. This computes a
plan only: no confirmation, inventory write, file save or interface integration.
`compute_restock_plan` returns positive shipments, total units, cost in integer
cents, projected warehouse inventory and remaining store demand. The exact
immutable input State is retained as `source_state`; a revision number alone
would not uniquely identify inputs. Applying a plan remains Stage 7.

## Network and reasoning

For each item independently, create source → warehouse edges with stock capacity,
warehouse → store edges with per-unit shipping cost, and store → sink edges with
demand capacity. The first and last edges cost zero. Each route's capacity can
be capped at min(warehouse stock, store demand) without excluding any feasible plan.

Every forward edge has a reverse residual edge, initially capacity zero, with
the opposite cost. After assigning q units forward, q units become available
on the reverse edge. Using that reverse edge revises a proposed assignment; it
does not send goods back from a store in the real world.

Start with zero flow. Bellman–Ford finds the cheapest residual source-to-sink
path, even when some edges have negative costs. Send the full bottleneck amount,
update forward and reverse capacities, and repeat until min(total stock, total
demand) units have been sent. Never stop merely because the next path is costly.

In the $101 greedy counterexample, first allocate W1→S1 for $1. The next path
uses W2→S1 ($2), reverses W1→S1 (−$1), and uses W1→S2 ($2). That augmentation
adds $3, yielding total $4 and the crossed allocation. Forward-only greed fails.

The correctness invariant is that the current flow is cheapest among feasible
flows with the same value. Zero flow starts with this property because forward
costs are nonnegative. A shortest residual augmentation preserves it: residual
edges represent every permissible increase and reassignment, and a cheaper
alternative would imply a cheaper augmenting choice or a negative-cost cycle.
At maximum flow, this gives the required minimum-cost maximum-fulfillment plan.
The separate audit checks absence of negative residual cycles using Floyd–Warshall
on a graph reconstructed from returned shipments, independently of solver internals.

## Time and space

Let V=n2+n3+2 and E=n2*n3+n2+n3 forward edges. Reverse edges double E, which
does not change big-O. Bellman–Ford takes O(VE) per augmentation. Let A be the
total augmentations across all items; A<=m since every augmentation ships at
least one whole unit, often many. For k items with both stock and demand positive,
runtime is O(n1(n2+n3)+n2*n3+kE+A*V*E). This is a quantity-dependent bound, not
a claim of strongly polynomial runtime. Integer bit-operation costs are separate.

Only one item's residual graph is kept at a time: O(V+E) working space, plus
O(n1(n2+n3)) projections and up to O(n1*n2*n3) positive shipment output entries.
Stage 6 improves shortest-path searches; it does not change the objective.

## Verification evidence

- 57 tests passed, including the original and partial UI examples, zero stock,
  zero demand, exact/excess/short supply, tied/free prices, multiple items, input
  immutability, same-revision branches, duplicate labels, and very large integers.
- 6,561 exhaustive small cases match the independent Stage 4 checker.
- 400 seeded multi-item rectangular instances match that checker per item.
- Independent audit: 65,536 exhaustive 2x2 cases with quantities/costs 0–3 match
  flat matrix enumeration. These domains overlap; counts are not additive.
- 200 larger instances pass feasibility and a Floyd–Warshall negative-cycle
  certificate. That certificate correctly rejects the $101 greedy allocation.
- Deliberately disabling reverse capacity, using the wrong reverse cost sign,
  and using the wrong store price all cause tests to reject the result.
- Original sample: 10 units, 1400 cents. Partial: 12 units, 2000 cents, two
  monitors still needed at Store Y. The input State remains unchanged.

Run `.venv/bin/python -B -m unittest discover -s tests -v` and
`.venv/bin/python -B tests/audit_optimizer.py` from the project folder.
After Stage 6, the default method is Dijkstra; use
`compute_restock_plan(state, method="bellman_ford")` to inspect this baseline.

Explain why reverse cost is negative, why Bellman–Ford is valid here, and why
shipping zero is not acceptable when stock and demand exist. Personal Stage 5
verification is pending; the user authorized implementing Stage 6 in the same
session after agent verification of Stage 5.
