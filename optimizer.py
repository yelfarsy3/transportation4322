"""Stages 5–6: successive shortest paths, with two verified search methods.

Pure calculation: no UI, file writes, or test-reference imports. Reverse edges
permit reassignment during planning; they do not represent actual deliveries.
"""
from collections.abc import Mapping
from dataclasses import dataclass
from heapq import heappop, heappush
from types import MappingProxyType

from data_model import State


@dataclass
class _Edge:
    to: int
    reverse: int
    capacity: int
    cost: int


@dataclass(frozen=True)
class _Shipment:
    item_id: str
    warehouse_id: str
    store_id: str
    quantity: int
    unit_cost_cents: int

    @property
    def subtotal_cents(self):
        return self.quantity * self.unit_cost_cents


@dataclass(frozen=True)
class _RestockPlan:
    """Internal output record, obtained only through compute_restock_plan.

    source_state retains the exact immutable input, not merely its revision.
    Projected values are not committed state. Confirmation belongs to Stage 7.
    """
    source_state: State
    shipments: tuple[_Shipment, ...]
    units_shipped: int
    total_cost_cents: int
    projected_inventory: Mapping[str, Mapping[str, int]]
    remaining_demand: Mapping[str, Mapping[str, int]]


def _add_edge(graph, start, end, capacity, cost):
    forward = _Edge(end, len(graph[end]), capacity, cost)
    backward = _Edge(start, len(graph[start]), 0, -cost)
    graph[start].append(forward)
    graph[end].append(backward)
    return forward


def _shortest_path(graph, source):
    """Bellman–Ford on positive-capacity residual edges, including negative costs."""
    distance = [None] * len(graph)
    previous = [None] * len(graph)
    distance[source] = 0
    for _ in range(len(graph) - 1):
        changed = False
        for vertex, edges in enumerate(graph):
            if distance[vertex] is None:
                continue
            for index, edge in enumerate(edges):
                if edge.capacity <= 0:
                    continue
                candidate = distance[vertex] + edge.cost
                if distance[edge.to] is None or candidate < distance[edge.to]:
                    distance[edge.to] = candidate
                    previous[edge.to] = (vertex, index)
                    changed = True
        if not changed:
            break
    # Correct successive shortest-path flow cannot have a reachable negative
    # cycle. Fail visibly if a future change breaks that invariant.
    for vertex, edges in enumerate(graph):
        if distance[vertex] is not None:
            for edge in edges:
                if edge.capacity > 0 and (distance[edge.to] is None or
                        distance[vertex] + edge.cost < distance[edge.to]):
                    raise RuntimeError('Residual graph contains a reachable negative-cost cycle')
    return distance, previous


def _shortest_path_dijkstra(graph, source, potentials):
    """Use reduced costs c(u,v)+p(u)-p(v), nonnegative on reachable edges.

    Run to exhaustion, not just to the sink, so every finite distance used to
    update potentials is final. None denotes unreachable, not a finite sentinel.
    """
    distance = [None] * len(graph)
    previous = [None] * len(graph)
    distance[source] = 0
    queue = [(0, source)]
    while queue:
        current, vertex = heappop(queue)
        if current != distance[vertex]:
            continue
        for index, edge in enumerate(graph[vertex]):
            if edge.capacity <= 0:
                continue
            reduced_cost = edge.cost + potentials[vertex] - potentials[edge.to]
            if reduced_cost < 0:
                raise RuntimeError('Negative reachable reduced cost violates Dijkstra invariant')
            candidate = current + reduced_cost
            if distance[edge.to] is None or candidate < distance[edge.to]:
                distance[edge.to] = candidate
                previous[edge.to] = (vertex, index)
                heappush(queue, (candidate, edge.to))
    for vertex, value in enumerate(distance):
        if value is not None:
            potentials[vertex] += value
    return distance, previous


def _solve_item(stock, need, costs, *, method='dijkstra', trace=None):
    """Internal solver on validated counts; returns matrix, cost, augmentation count.

    If trace is a list, one read-only record per augmenting path is appended
    (vertex sequence source→sink, amount, original-cost sum, potentials). Recording
    never alters the search, so traced and untraced runs are identical.
    """
    nw, ns = len(stock), len(need)
    source, sink = nw + ns, nw + ns + 1
    graph = [[] for _ in range(nw + ns + 2)]
    for w, count in enumerate(stock):
        _add_edge(graph, source, w, count, 0)
    routes = []
    for w in range(nw):
        routes.append([_add_edge(graph, w, nw+s, min(stock[w], need[s]), costs[w][s])
                       for s in range(ns)])
    for s, count in enumerate(need):
        _add_edge(graph, nw+s, sink, count, 0)
    target = min(sum(stock), sum(need))
    flow = cost = augmentations = 0
    # Initially all positive-capacity edges have nonnegative original cost.
    potentials = [0] * len(graph)
    while flow < target:
        if method == 'bellman_ford':
            distance, previous = _shortest_path(graph, source)
        else:
            distance, previous = _shortest_path_dijkstra(graph, source, potentials)
        if distance[sink] is None:
            raise RuntimeError('Complete transportation network cannot reach required flow')
        path = []
        vertex = sink
        while vertex != source:
            if previous[vertex] is None or len(path) >= len(graph):
                raise RuntimeError('Invalid shortest-path predecessor chain')
            parent, index = previous[vertex]
            path.append((parent, index))
            vertex = parent
        amount = min(target-flow, *(graph[v][i].capacity for v, i in path))
        # Reduced distances differ from actual currency cost. Sum original
        # edge costs, including negative reverse costs, for BOTH methods.
        path_cost = sum(graph[v][i].cost for v, i in path)
        for v, i in path:
            edge = graph[v][i]
            edge.capacity -= amount
            graph[edge.to][edge.reverse].capacity += amount
        flow += amount
        cost += amount * path_cost
        augmentations += 1
        if trace is not None:
            trace.append({'vertices': (source, *(graph[v][i].to for v, i in reversed(path))),
                          'amount': amount, 'path_cost': path_cost,
                          'potentials': tuple(potentials) if method == 'dijkstra' else None})
    allocation = tuple(tuple(min(stock[w], need[s]) - routes[w][s].capacity
                             for s in range(ns)) for w in range(nw))
    if cost != sum(allocation[w][s] * costs[w][s] for w in range(nw) for s in range(ns)):
        raise RuntimeError('Residual costs disagree with final shipment costs')
    return allocation, cost, augmentations


def _freeze_matrix(matrix):
    return MappingProxyType({key: MappingProxyType(dict(row)) for key, row in matrix.items()})


def compute_restock_plan(state: State, *, method='dijkstra') -> _RestockPlan:
    """Maximize shipments per item, then minimize total cost; never mutate state.

    Returns immutable positive shipments, cost, projected stock and unmet demand.
    No fairness objective or shared transport capacity. Ties may yield any optimum.
    Costs and all arithmetic remain integer cents, even beyond floating-point range.
    method='bellman_ford' retains the Stage 5 baseline; default is heap Dijkstra
    with vertex potentials. Equal-cost plans need not have identical allocations.
    """
    if not isinstance(state, State):
        raise TypeError('compute_restock_plan requires a validated State')
    if method not in ('dijkstra', 'bellman_ford'):
        raise ValueError('method must be dijkstra or bellman_ford')
    warehouses, stores = tuple(state.warehouses), tuple(state.stores)
    inventory = {w: dict(row) for w, row in state.inventory.items()}
    demand = {s: dict(row) for s, row in state.demand.items()}
    costs = [[state.shipping_costs_cents[w][s] for s in stores] for w in warehouses]
    shipments = []
    total_cost = units = 0
    for item in state.items:
        stock = [state.inventory[w][item] for w in warehouses]
        need = [state.demand[s][item] for s in stores]
        if not any(stock) or not any(need):
            continue
        allocation, cost, _ = _solve_item(stock, need, costs, method=method)
        total_cost += cost
        for wi, w in enumerate(warehouses):
            for si, s in enumerate(stores):
                quantity = allocation[wi][si]
                if quantity:
                    shipments.append(_Shipment(item, w, s, quantity, costs[wi][si]))
                    inventory[w][item] -= quantity
                    demand[s][item] -= quantity
                    units += quantity
    return _RestockPlan(state, tuple(shipments), units, total_cost,
                        _freeze_matrix(inventory), _freeze_matrix(demand))


def trace_restock_plan(state: State):
    """Replay record for the explorer: the augmenting paths compute_restock_plan selects.

    Vertex numbering per item: warehouses 0..W-1, stores W..W+S-1, then source, sink.
    It records chosen paths only, not the shortest-path search that found them.
    """
    if not isinstance(state, State):
        raise TypeError('trace_restock_plan requires a validated State')
    warehouses, stores = tuple(state.warehouses), tuple(state.stores)
    costs = [[state.shipping_costs_cents[w][s] for s in stores] for w in warehouses]
    items = []
    for item in state.items:
        stock = [state.inventory[w][item] for w in warehouses]
        need = [state.demand[s][item] for s in stores]
        if not any(stock) or not any(need):
            continue
        paths = []
        allocation, cost, _ = _solve_item(stock, need, costs, trace=paths)
        items.append({'item_id': item, 'stock': tuple(stock), 'need': tuple(need),
                      'paths': tuple(paths), 'allocation': allocation, 'cost_cents': cost})
    return tuple(items)
