# Demonstration and explanation guide

Prepared by the agent on 2026-11-09. This is study material, not a claim that the
student has performed or understood these checks. Course authority:
[general instructions, pp. 1–2](reference/general-instructions.pdf) and
[transportation assignment, p. 1](reference/assignment-transportation.pdf).

## Demonstrate from known data

Use a separate working JSON file (README explains `TRANSPORTATION_STATE_PATH`),
or explicitly reset demo data with the checkbox. Do not reset valuable working
inventory merely to present the example.

1. Show the original tables. Supply: 9 keyboards, 5 monitors. Demand: 7 keyboards,
   3 monitors. Explain that the store table records missing quantities.
2. Preview: 10 units, $14. Cancel and show that nothing changed. Preview again,
   confirm, and inspect stock A=(2 keyboards,1 monitor), B=(0,1), demand all zero.
   A second preview has no shipments and cannot be confirmed.
3. Reset the demo. Edit Store Y monitors from 2 to 6. Finish the cell with Tab,
   inspect the displayed 6, then Save. Preview: 12 of 14 units, $20, 2 monitors
   remain at Y. Confirm and reopen the app: the 2 monitors are still outstanding.
4. Preview with no monitor stock: no shipments; confirmation disabled. Cancel.
   Add 2 monitors to Warehouse B through the quantity shortcut. Preview: 2 units,
   $2.00. Confirm: all demand zero.
5. Show batch validation: change two cells, make one negative, and Save. Explain
   why no part of that batch is saved. Discard to return to the saved scenario.
6. Explain that Reload discards unsaved drafts and previews. A plan calculated
   before data changed cannot be applied as though it were current.

These expected figures follow hand calculations: the full sample sends A→X
3 keyboards + 1 monitor at $2 each, and B→Y 4 keyboards + 2 monitors at $1 each.
For the shortage example, keyboards still cost $10; monitors cost
A→X 1×$2 + B→Y 3×$1 + A→Y 1×$5 = $10. Every cheap B monitor is used and X's
single monitor is filled from A; the remaining A monitor goes to Y. Total $20.

## Explain the architecture

The UI converts text to exact integers/cents. The immutable data model rejects
inconsistent matrices and negative counts. Availability determines how many units
can ship. The optimizer proposes routes without modifying anything. Operations
validate and apply a current preview. Storage publishes the complete candidate
before memory is updated. A failed write cannot leave half of a batch applied.

Batch editing is a UI convenience and one transaction; it does not change the
optimization objective. A draft is separate from saved state. A preview is
separate again. None of these states should silently replace another.

## Defend the algorithm

For each item, build source→warehouse→store→sink edges. Warehouse capacities are
stock; store capacities are demand. Shipping edges carry per-unit costs. A reverse
residual edge lets a later augmentation undo an earlier choice. This is why picking
the cheapest route greedily is insufficient (see the $4 versus $101 test).

Ship the largest possible number first; among such flows minimize cost. Shortage
fairness is not a second objective. Items are independent because there are no
shared route/vehicle capacities and every warehouse can reach every store.

Bellman–Ford supports negative residual costs. Dijkstra uses potentials p and
reduced costs c'(u,v)=c(u,v)+p(u)−p(v). Potentials telescope on a path, so shortest
path ordering is preserved. Reachable reduced costs stay nonnegative; updates
are essential. Total money uses original costs, not reduced distances.

For n2 warehouses and n3 stores, V=n2+n3+2 and E=n2*n3+n2+n3 forward edges plus
reverse edges. At most m augmentations are needed across items, where m is total
missing units (actual augmentations send a full path bottleneck). With the lazy
heap and this graph, a shortest-path search is O(E log V). A coarse overall bound
is O(n1*n2*n3 + m*n2*n3*log(n2+n3)), ignoring integer bit-operation costs. The bound
is pseudo-polynomial in numeric m. Graph storage is O(V+E) per item; the heap can
use O(E); the returned shipment list across all items can use O(n1*n2*n3).
See [Stage 6](stage6-understanding-check.md) for the detailed implementation analysis.

## Explain what the checks establish

Small instances: independent brute force and a separate flat enumeration agree
with both production solvers. Large instances: feasibility, maximum fulfillment,
identical objectives and independent residual-cycle checks. Deliberate defects
show that some important mistakes would be detected. Persistence tests include
actual child-process exits before and after file replacement. UI tests use real
Streamlit script execution; browser checks additionally exercise grid editing.

Finite tests provide evidence, not a proof over all inputs. Correctness arguments
and invariants still matter. Faster measured time on this machine is not a universal
speed guarantee. Prepared benchmarks are in `stage10-optimizer-audit.log`.

## Personal verification gate

Explain without reading: why prices do not change maximum possible shipments;
why Dijkstra needs potentials; why a cheap first choice may need reversal;
why Save is atomic; why preview differs from confirmation; why reload is needed
after an ambiguous save failure; and which assumptions would fail with a shared
truck capacity or fairness constraint. Record actual observations and your own
explanation separately. Do not present this document as your own performed checks.
