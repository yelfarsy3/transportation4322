"""Stage 3: count possible shipments without choosing routes or changing stock."""
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

from data_model import State, validate_nonnegative_integer


@dataclass(frozen=True)
class ItemAvailability:
    """Totals for one item; derived values cannot become stale independently."""

    supply: int
    demand: int

    def __post_init__(self):
        # Totals may exceed the per-cell storage limit; they are not stored cells.
        validate_nonnegative_integer(self.supply, "supply")
        validate_nonnegative_integer(self.demand, "demand")

    @property
    def shippable(self) -> int:
        return min(self.supply, self.demand)

    @property
    def shortage(self) -> int:
        return self.demand - self.shippable


def calculate_availability(state: State) -> Mapping[str, ItemAvailability]:
    """Return read-only per-item totals for an already validated State.

    Every warehouse can supply every store, without shared capacity limits.
    Thus min(supply, demand) units of each item can be shipped. Shipping costs
    affect route selection later, but not these counts. No per-store shortage
    allocation or shipment cost is determined here.

    Time: O(n1 * (n2 + n3)); auxiliary space: O(n1). Counts use Python integers.
    """
    if not isinstance(state, State):
        raise TypeError("calculate_availability requires a validated State")
    return MappingProxyType({
        item_id: ItemAvailability(
            supply=sum(row[item_id] for row in state.inventory.values()),
            demand=sum(row[item_id] for row in state.demand.values()),
        )
        for item_id in state.items
    })
