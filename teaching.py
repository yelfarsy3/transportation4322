"""Presentation-only analyses. Never used to plan or confirm a restock.

- cheapest_first: the naive greedy plan, shown only for comparison.
- certify: an independent optimality certificate for any allocation. It
  rebuilds the residual network from the final shipments alone (no optimizer
  internals) and searches for a negative-cost cycle with Bellman–Ford. A
  maximum-quantity allocation with no such cycle has minimum cost; a cycle that
  is found is a concrete cheaper rearrangement.
"""
from dataclasses import dataclass

from data_model import State


@dataclass(frozen=True)
class CycleStep:
    warehouse_id: str
    store_id: str
    more: bool            # True: ship more on this route; False: ship less
    unit_cost_cents: int


@dataclass(frozen=True)
class ItemCertificate:
    item_id: str
    units: int
    max_units: int
    cycle: tuple          # tuple[CycleStep, ...]; empty when no cheaper loop exists
    cycle_cost_cents: int  # per unit moved around the loop; negative means a saving

    @property
    def optimal(self):
        return self.units == self.max_units and not self.cycle


def _allocation_from_plan(plan):
    allocation = {}
    for shipment in plan.shipments:
        allocation.setdefault(shipment.item_id, {})[(shipment.warehouse_id, shipment.store_id)] = shipment.quantity
    return allocation


def cheapest_first(state: State):
    """Greedy demonstration: fill the cheapest open route first, per item.

    Returns (allocation {item: {(w, s): qty}}, total cost in cents). It ships
    the maximum quantity on a complete network, but not always at minimum cost.
    """
    if not isinstance(state, State):
        raise TypeError('cheapest_first requires a validated State')
    W, S = list(state.warehouses), list(state.stores)
    routes = sorted(((state.shipping_costs_cents[w][s], wi, si) for wi, w in enumerate(W)
                     for si, s in enumerate(S)))
    allocation, total = {}, 0
    for item in state.items:
        left = [state.inventory[w][item] for w in W]
        need = [state.demand[s][item] for s in S]
        chosen = {}
        for cost, wi, si in routes:
            amount = min(left[wi], need[si])
            if amount:
                chosen[(W[wi], S[si])] = amount
                left[wi] -= amount
                need[si] -= amount
                total += amount * cost
        allocation[item] = chosen
    return allocation, total


def _certify_item(state, item, chosen):
    W, S = list(state.warehouses), list(state.stores)
    nw, ns = len(W), len(S)
    source, sink, n = nw + ns, nw + ns + 1, nw + ns + 2
    stock = [state.inventory[w][item] for w in W]
    need = [state.demand[s][item] for s in S]
    sent = [0] * nw
    got = [0] * ns
    edges = []  # (u, v, cost, route or None, more)
    for wi, w in enumerate(W):
        for si, s in enumerate(S):
            cost = state.shipping_costs_cents[w][s]
            x = chosen.get((w, s), 0)
            sent[wi] += x
            got[si] += x
            edges.append((wi, nw + si, cost, (wi, si), True))      # can always ship more
            if x:
                edges.append((nw + si, wi, -cost, (wi, si), False))  # can ship less
    if any(sent[i] > stock[i] for i in range(nw)) or any(got[j] > need[j] for j in range(ns)):
        raise ValueError('Allocation exceeds stock or demand')
    for wi in range(nw):
        if stock[wi] > sent[wi]:
            edges.append((source, wi, 0, None, True))   # unused stock could be used
        if sent[wi]:
            edges.append((wi, source, 0, None, False))  # used stock could be released
    for si in range(ns):
        if need[si] > got[si]:
            edges.append((nw + si, sink, 0, None, True))
        if got[si]:
            edges.append((sink, nw + si, 0, None, False))
    # Bellman–Ford from a virtual root joined to every vertex at cost 0.
    distance = [0] * n
    previous = [None] * n
    touched = None
    for _ in range(n + 1):  # n+1 vertices with the root; a change on pass n+1 means a cycle
        touched = None
        for index, (u, v, cost, _, _) in enumerate(edges):
            if distance[u] + cost < distance[v]:
                distance[v] = distance[u] + cost
                previous[v] = index
                touched = v
        if touched is None:
            break
    units = sum(sent)
    max_units = min(sum(stock), sum(need))
    if touched is None:
        return ItemCertificate(item, units, max_units, (), 0)
    vertex = touched
    for _ in range(n):  # step back n times to land inside the cycle
        vertex = edges[previous[vertex]][0]
    cycle_edges, start = [], vertex
    while True:
        index = previous[vertex]
        cycle_edges.append(edges[index])
        vertex = edges[index][0]
        if vertex == start:
            break
    cycle_edges.reverse()
    steps = tuple(CycleStep(W[r[0]], S[r[1]], more, state.shipping_costs_cents[W[r[0]]][S[r[1]]])
                  for _, _, _, r, more in cycle_edges if r is not None)
    return ItemCertificate(item, units, max_units, steps, sum(e[2] for e in cycle_edges))


def certify(state: State, plan=None, *, allocation=None):
    """Certificates for every item, from a plan or an explicit allocation."""
    if not isinstance(state, State):
        raise TypeError('certify requires a validated State')
    if (plan is None) == (allocation is None):
        raise ValueError('Pass exactly one of plan or allocation')
    allocation = _allocation_from_plan(plan) if plan is not None else allocation
    return tuple(_certify_item(state, item, allocation.get(item, {})) for item in state.items)
