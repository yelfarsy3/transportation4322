# Stage 7: preview, cancel and confirm

`operations.py` introduces RestockSession, which owns the actual current state
and one active preview. Use session.preview(), session.cancel(preview), and
session.confirm(preview). The optimizer still only computes proposed shipments.

Preview never changes stock, demand or revision. A new preview replaces the old
handle. Cancel discards it. Confirm accepts only the exact active handle, checks
the entire source snapshot, independently reconstructs the deductions, and
publishes a complete new State. Revision increases once. Repeating confirmation,
using a canceled/replaced/foreign handle, or replaying after reset is rejected.

Quantity/price edits invalidate previews when values change. Failed edits and
no-ops leave the preview valid. Reset always increments revision and cancels the
preview, even when restoring identical quantities. Empty plans may be inspected
but cannot be confirmed. With no stock, demand remains outstanding.

`validate_plan` checks IDs, positive integer shipments, unique item/route entries,
current prices, capacities, maximum fulfillment by item, totals and projections.
It does not independently prove minimum cost; the verified optimizer provides
that. `apply_restock` is a pure candidate-state helper. Actual commitment belongs
to RestockSession.confirm; in Stage 8 this includes saving before publishing.

The original example confirms 10 units for $14, leaving 4 units in warehouses
and zero demand. The partial example confirms 12 units for $20, retaining 2
monitors needed at Store Y. Adding 2 monitors to B then produces a new two-unit,
$2 plan. The new plan ships only the outstanding demand.

Correctness argument: all deductions are built on detached data. Every shipment
is checked before a candidate State is constructed. Until the commit succeeds,
the old State and active preview remain intact. Clearing the active handle after
commit makes the same confirmation unusable again. These are single-user local
session semantics, not an authentication or concurrent database mechanism.

The normal suite covers 81 stock/demand combinations with both solvers and all
2,401 length-four traces over preview/confirm/cancel/add stock/add demand/change
price/reset, comparing every step with an independent scalar model. It also
rejects malformed/tampered plans and tests revision overflow.

Explain why checking revision alone is insufficient, why reset invalidates an
old preview, why zero shipments cannot be confirmed, and why preview and confirm
must remain separate. Personal Stage 7 verification is pending; agent verification
precedes the jointly authorized Stage 8 implementation.
