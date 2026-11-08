# Stage 6: Dijkstra with vertex potentials

Both solvers are in `optimizer.py`. Default `compute_restock_plan(state)` uses
Dijkstra; `compute_restock_plan(state, method="bellman_ford")` retains the Stage 5
baseline. Both return maximum units, minimum cost, positive shipments, projected
inventory and remaining demand without changing the input. Tied allocations may
differ while achieving the same objective. Neither method applies a restock.

## Why ordinary Dijkstra was not enough

After a shipment is assigned, its residual reverse edge has negative original
cost. Ordinary Dijkstra cannot generally use those edge weights correctly.
Bellman–Ford handles them but costs O(VE) per augmentation. Potentials let us
reweight reachable residual edges to be nonnegative without changing which
source-to-sink path is cheapest.

Give each vertex a potential p(v). Define reduced cost:

    c'(u,v) = c(u,v) + p(u) - p(v)

On any source-to-sink path, internal potentials cancel. Its reduced cost is its
original cost plus p(source)−p(sink), the same offset for every candidate path.
Thus choosing a cheapest reduced-cost path also chooses a cheapest original path.

Initially all potentials are zero. Positive-capacity edges have nonnegative
original costs; negative reverse edges have zero capacity and cannot be used.
Run Dijkstra on positive-capacity edges. Let d(v) be its final reduced distance.
For every reached vertex, update p(v) to p(v)+d(v).

The shortest-path inequality says d(v)<=d(u)+c'(u,v). Therefore the updated reduced
cost is c'(u,v)+d(u)−d(v)>=0. Every edge on the selected shortest path is tight,
so its updated reduced cost is zero; its newly available reverse edge also has
zero reduced cost. This preserves the invariant for the next augmentation.

We leave unreachable potentials unchanged. No new edge to a previously
unreachable vertex is activated: added reverse edges connect vertices on the
selected path, all already reached. The invariant is needed on reachable edges.

The implementation finishes Dijkstra's search before updating potentials. Stopping
as soon as the sink is removed from the heap would leave other tentative distances
unfinished; using those values as potentials can break the invariant. A dedicated
test exercises a vertex whose initial distance 10 later improves to 3.

Actual charges still use original edge costs, including negative reverse costs.
Reduced distances are a search device, not currency totals. Final shipment
subtotals are independently reconciled with the accumulated cost.

## Complexity and measured performance

V=n2+n3+2; E=n2*n3+n2+n3 forward edges plus a constant-factor number of reverse
edges. Heap Dijkstra takes O(E log V) per augmentation (lazy heap entries can use
O(E) space). If A augmentations are performed across k active item types, runtime
is O(n1(n2+n3)+n2*n3+kE+A E log V). Since A<=m and k<=n1, a straightforward bound
for positive dimensions is O(n1*n2*n3 + m*n2*n3*log(n2+n3)). This still depends on
the numerical demand m; integer bit costs are not included in this arithmetic bound.

The graph is processed one item at a time: O(V+E) solver workspace. Projected
tables need O(n1(n2+n3)); output can contain O(n1*n2*n3) positive shipments. The
source State is retained by reference rather than copied again.

Measured on this Apple Silicon Mac, Python 3.14.7. Each row uses one fixed seeded
input, both methods warmed up, alternating order, median of three timed runs.
Both methods' results are checked on every run. These are observations, not
performance guarantees or a broad benchmark study.

| Warehouses × stores × items | Bellman–Ford | Dijkstra | Observed ratio |
|---|---:|---:|---:|
| 4 × 4 × 2 | 0.000179 s | 0.000140 s | 1.28× |
| 12 × 12 × 3 | 0.004416 s | 0.002451 s | 1.80× |
| 30 × 30 × 3 | 0.072483 s | 0.030051 s | 2.41× |
| 60 × 60 × 3 | 0.694003 s | 0.202872 s | 3.42× |

Raw results: `stage6-independent-audit.log`. Timing depends on the machine and input;
the asymptotic improvement follows from the algorithm, not these four timings.

## Verification and reproducibility

63 tests passed on the first Stage 6 run. The full suite includes exhaustive
comparison of both methods against the independent Stage 4 oracle on 6,561 cases,
plus all previous state, availability, reference and solver tests. Additional
tests cover unreachable vertices, zero prices, invalid method names, stale heap
distances, potential updates and the negative reduced-cost guard.

The separate Stage 6 audit checks:

- Both methods against flat matrix enumeration on all 65,536 2x2 instances with
  quantities and costs 0–3. These overlap the smaller domain, not extra distinct cases.
- 300 seeded small multi-item inputs against Stage 4 enumeration.
- 150 larger multi-item inputs: identical objective values, feasible projections,
  and no negative residual cycles certified independently with Floyd–Warshall.
- Three deliberate in-memory defects: omitted potential updates, reversed signs,
  and charging reduced distances as actual cost. All are rejected by runtime
  invariants/tests. No intentionally defective source was written to disk.

Commands from the project folder:

```sh
.venv/bin/python -B -m unittest discover -s tests -v
.venv/bin/python -B tests/audit_stage6.py
```

To inspect the example yourself:

```sh
.venv/bin/python -B - <<'PY'
from pathlib import Path
from data_model import State
from optimizer import compute_restock_plan
state = State.from_json(Path('data/sample.json').read_text())
for method in ['bellman_ford', 'dijkstra']:
    plan = compute_restock_plan(state, method=method)
    print(method, plan.units_shipped, plan.total_cost_cents)
    for shipment in plan.shipments:
        print(shipment)
PY
```

Both methods should print 10 units and 1400 cents for this sample. Explain why
negative original costs can coexist with nonnegative reduced costs, why path
order is preserved, and why prices must be computed from original costs.

Agent implementation/verification gates for Stages 5 and 6 are complete. Personal
understanding checks remain for the student, not inferred from passing agent tests.
Stage 7 will add preview cancellation, stale-state validation and once-only
confirmation. None of those transaction features is claimed complete here.
