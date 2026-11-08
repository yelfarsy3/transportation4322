"""Tiny-instance test oracle only. Never import this into the application.

Enumerates allocations directly, without flow graphs or production helpers.
Search limits raise an error; an incomplete search never returns an optimum.
"""
from dataclasses import dataclass


class SearchLimitExceeded(RuntimeError):
    """This instance needs more search than the configured test budget permits."""


@dataclass(frozen=True)
class _ReferenceResult:
    """Internal output record; callers obtain it through solve_tiny only."""
    units: int
    cost_cents: int
    shipments: tuple[tuple[int, ...], ...]


def solve_tiny(supply, demand, costs_cents, *, max_nodes=250_000) -> _ReferenceResult:
    """Find maximum units, then minimum cost, for ONE item type.

    Inputs: sequences of warehouse stocks, store demands, and warehouse-row
    per-unit costs in cents. All entries must be nonnegative integers (not bool).
    Supports 1–3 warehouses/stores and at most 20 units in each quantity cell.
    Costs need not be small. The node budget bounds even valid but expensive cases.
    Tied optima may have different allocations; only the objective is guaranteed.
    Inputs are copied, never mutated. Returns immutable shipments and totals.
    """
    def integer(value, label):
        if type(value) is not int or value < 0:
            raise ValueError(f'{label} must be a nonnegative integer')

    integer(max_nodes, 'max_nodes')
    if max_nodes == 0:
        raise ValueError('max_nodes must be positive')
    try:
        stock = list(supply)
        needs = list(demand)
        costs = [list(row) for row in costs_cents]
    except TypeError as error:
        raise ValueError('Expected sequences of quantities and cost rows') from error
    nw, ns = len(stock), len(needs)
    if not (1 <= nw <= 3 and 1 <= ns <= 3):
        raise ValueError('Tiny reference supports 1–3 warehouses and stores')
    if len(costs) != nw or any(len(row) != ns for row in costs):
        raise ValueError('Cost dimensions must match supply and demand')
    for value in stock + needs:
        integer(value, 'quantity')
        if value > 20:
            raise ValueError('Tiny reference quantities must not exceed 20 per cell')
    for row in costs:
        for value in row:
            integer(value, 'cost')

    allocation = [[0] * ns for _ in stock]
    best_key = None
    best = None
    nodes = 0

    def visit(edge, units, cost):
        nonlocal best_key, best, nodes
        nodes += 1
        if nodes > max_nodes:
            raise SearchLimitExceeded(f'Exceeded {max_nodes} search nodes; no optimum returned')
        if edge == nw * ns:
            key = (-units, cost)
            if best_key is None or key < best_key:
                best_key = key
                best = _ReferenceResult(units, cost, tuple(tuple(row) for row in allocation))
            return
        w, s = divmod(edge, ns)
        # Try every feasible amount on this route, including zero. Remaining
        # stock/demand enforce row and column constraints without a solver.
        for quantity in range(min(stock[w], needs[s]) + 1):
            allocation[w][s] = quantity
            stock[w] -= quantity
            needs[s] -= quantity
            visit(edge + 1, units + quantity, cost + quantity * costs[w][s])
            stock[w] += quantity
            needs[s] += quantity
        allocation[w][s] = 0

    visit(0, 0, 0)
    return best
