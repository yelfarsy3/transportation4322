"""Stage 7 application operations. Optimizer results are proposals, not edits."""
from dataclasses import dataclass

from data_model import State, ValidationError, validate_nonnegative_integer
from optimizer import _RestockPlan, _Shipment, compute_restock_plan


class PlanError(ValidationError):
    """A plan is stale, infeasible or internally inconsistent."""


class PreviewError(ValidationError):
    """This preview is no longer active, or has no shipments to confirm."""


def _project(state, plan):
    """Independently reconstruct projections; never trust the supplied totals."""
    if not isinstance(state, State) or not isinstance(plan, _RestockPlan):
        raise PlanError('Expected a validated State and optimizer plan')
    if plan.source_state != state:
        raise PlanError('State has changed since this plan was calculated')
    data = state.to_dict()
    by_item = dict.fromkeys(state.items, 0)
    units = cost = 0
    seen = set()
    if not isinstance(plan.shipments, tuple):
        raise PlanError('Shipments must be an immutable tuple')
    for shipment in plan.shipments:
        if not isinstance(shipment, _Shipment):
            raise PlanError('Invalid shipment record')
        item, w, s = shipment.item_id, shipment.warehouse_id, shipment.store_id
        if (not all(isinstance(key, str) for key in (item, w, s))
                or item not in state.items or w not in state.warehouses or s not in state.stores):
            raise PlanError('Unknown item, warehouse or store')
        if (item, w, s) in seen:
            raise PlanError('Duplicate shipment route for an item')
        seen.add((item, w, s))
        q, price = shipment.quantity, shipment.unit_cost_cents
        validate_nonnegative_integer(q, 'shipment quantity')
        validate_nonnegative_integer(price, 'shipment price')
        if q == 0 or price != state.shipping_costs_cents[w][s]:
            raise PlanError('Shipment must be positive and use the current price')
        data['inventory'][w][item] -= q
        data['demand'][s][item] -= q
        if data['inventory'][w][item] < 0 or data['demand'][s][item] < 0:
            raise PlanError('Shipment exceeds stock or demand')
        units += q
        cost += q * price
        by_item[item] += q
    for item in state.items:
        maximum = min(sum(row[item] for row in state.inventory.values()),
                      sum(row[item] for row in state.demand.values()))
        if by_item[item] != maximum:
            raise PlanError('Plan does not ship the maximum quantity for each item')
    validate_nonnegative_integer(plan.units_shipped, 'total units')
    validate_nonnegative_integer(plan.total_cost_cents, 'total cost')
    if (units, cost) != (plan.units_shipped, plan.total_cost_cents):
        raise PlanError('Plan totals disagree with its shipments')
    # Validate types too: Python equality alone considers True equal to 1.
    claimed = state.to_dict()
    claimed['inventory'] = plan.projected_inventory
    claimed['demand'] = plan.remaining_demand
    validated = State.from_dict(claimed)
    if validated.inventory != data['inventory'] or validated.demand != data['demand']:
        raise PlanError('Plan projections disagree with its shipments')
    return data


def validate_plan(state, plan):
    """Check freshness, maximum fulfillment, feasibility and consistency.

    This does NOT independently prove global minimum cost. The tested optimizer
    supplies optimality; these checks protect the application transition.
    """
    _project(state, plan)


def apply_restock(state, plan):
    """Pure candidate transition. RestockSession.confirm owns actual commitment."""
    data = _project(state, plan)
    if plan.units_shipped == 0:
        raise PreviewError('No shipments are available to confirm')
    data['revision'] += 1
    return State.from_dict(data)


@dataclass(frozen=True)
class _Preview:
    """Session-owned handle: only the exact active object may be confirmed."""
    plan: _RestockPlan

    @property
    def can_confirm(self):
        return self.plan.units_shipped > 0


class RestockSession:
    """One local user's application session. Previews are never persisted."""
    def __init__(self, state, *, store=None):
        if not isinstance(state, State):
            raise TypeError('RestockSession requires a validated State')
        self._state = state
        self._pending = None
        self._store = store

    @classmethod
    def open(cls, store):
        """Open an existing save; explicit store.initialize handles first use."""
        return cls(store.load(), store=store)

    def reload(self):
        if self._store is None:
            raise PreviewError('This session has no persistent store to reload')
        state = self._store.load()
        self._state = state
        self._pending = None
        return state

    @property
    def state(self):
        return self._state

    @property
    def pending_preview(self):
        return self._pending

    def preview(self, *, method='dijkstra'):
        plan = compute_restock_plan(self._state, method=method)
        validate_plan(self._state, plan)
        self._pending = _Preview(plan)
        return self._pending

    def _require_active(self, preview):
        if preview is None or preview is not self._pending:
            raise PreviewError('Preview is canceled, replaced, already applied, or from another session')

    def cancel(self, preview):
        self._require_active(preview)
        self._pending = None

    def _commit(self, candidate):
        if self._store is not None:
            # Publish in-memory state and retire the preview only after saving.
            self._store.commit(self._state, candidate)
        self._state = candidate
        self._pending = None
        return candidate

    def confirm(self, preview):
        self._require_active(preview)
        candidate = apply_restock(self._state, preview.plan)
        return self._commit(candidate)

    def edit_quantity(self, table, location_id, item_id, quantity, operation='set'):
        candidate = self._state.with_quantity(table, location_id, item_id, quantity, operation)
        return self._state if candidate is self._state else self._commit(candidate)

    def edit_shipping_cost(self, warehouse_id, store_id, cents):
        candidate = self._state.with_shipping_cost(warehouse_id, store_id, cents)
        return self._state if candidate is self._state else self._commit(candidate)

    def edit_tables(self, *, expected_state, inventory=None, demand=None, shipping_costs_cents=None):
        """Validate and save an entire draft once, never one cell at a time.

        Each supplied table must have the exact original IDs and dimensions.
        Unsupplied tables remain unchanged. A single invalid cell rejects all edits.
        The caller must supply the snapshot on which its draft was based.
        """
        if not isinstance(expected_state, State) or expected_state != self._state:
            raise ValidationError('Data changed while editing; reload before saving this draft')
        data = self._state.to_dict()
        for name, table in (('inventory', inventory), ('demand', demand),
                            ('shipping_costs_cents', shipping_costs_cents)):
            if table is not None:
                data[name] = table
        checked = State.from_dict(data)
        if checked == self._state:
            return self._state
        data['revision'] += 1
        return self._commit(State.from_dict(data))

    def reset(self, sample):
        if not isinstance(sample, State):
            raise TypeError('Reset requires a validated sample State')
        for catalog in ('items', 'warehouses', 'stores'):
            if set(getattr(sample, catalog)) != set(getattr(self._state, catalog)):
                raise ValidationError('Reset must preserve item and location IDs')
        data = sample.to_dict()
        # Even resetting identical quantities changes revision and cancels preview.
        data['revision'] = self._state.revision + 1
        return self._commit(State.from_dict(data))
