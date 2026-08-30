from __future__ import annotations

import math
import random
from collections.abc import Iterable

from tests.helpers import node, scenario
from two_stage_router.graph import Graph, dijkstra
from two_stage_router.model import Edge, Shelter
from two_stage_router.planner import plan_evacuation


def bellman_ford(
    node_ids: tuple[str, ...], edges: tuple[Edge, ...], start: str
) -> dict[str, float]:
    distances = {node_id: math.inf for node_id in node_ids}
    distances[start] = 0
    directed = tuple(
        item
        for edge in edges
        for item in (
            (edge.source, edge.target, edge.weight),
            (edge.target, edge.source, edge.weight),
        )
    )
    for _ in range(len(node_ids) - 1):
        changed = False
        for source, target, weight in directed:
            candidate = distances[source] + weight
            if candidate < distances[target]:
                distances[target] = candidate
                changed = True
        if not changed:
            break
    return distances


def test_dijkstra_matches_independent_bellman_ford_on_small_graphs() -> None:
    randomizer = random.Random(20260830)
    for size in range(2, 9):
        ids = tuple(f"n{index}" for index in range(size))
        edges = []
        for left in range(size):
            for right in range(left + 1, size):
                if randomizer.random() < 0.42:
                    edges.append(Edge(ids[left], ids[right], randomizer.randint(1, 20)))
        graph = Graph(tuple(node(node_id) for node_id in ids), tuple(edges))
        for start in ids:
            actual = dijkstra(graph, start)
            expected = bellman_ford(ids, tuple(edges), start)
            for target in ids:
                if math.isinf(expected[target]):
                    assert target not in actual
                else:
                    assert actual[target].distance == expected[target]


def simple_paths(
    adjacency: dict[str, tuple[tuple[str, float], ...]],
    start: str,
    targets: frozenset[str],
) -> Iterable[tuple[tuple[str, ...], float]]:
    stack = [(start, (start,), 0.0)]
    while stack:
        current, path, distance = stack.pop()
        if current in targets:
            yield path, distance
        for neighbour, weight in adjacency[current]:
            if neighbour not in path:
                stack.append((neighbour, path + (neighbour,), distance + weight))


def test_complete_plan_matches_exhaustive_simple_path_oracle() -> None:
    nodes = tuple(
        node(name) for name in ("start", "h1", "h2", "a", "b", "x", "s1", "s2")
    )
    edges = (
        Edge("start", "h1", 1),
        Edge("start", "h2", 2),
        Edge("h1", "a", 1),
        Edge("h2", "b", 2),
        Edge("a", "x", 2),
        Edge("b", "x", 1),
        Edge("x", "s1", 3),
        Edge("a", "s2", 9),
        Edge("b", "s2", 2),
    )
    hazardous = frozenset({"start", "h1", "h2"})
    shelters = (Shelter("one", "s1"), Shelter("two", "s2"))
    case = scenario(
        nodes=nodes,
        edges=edges,
        start="start",
        shelters=shelters,
        hazardous=hazardous,
    )
    graph = Graph(nodes, edges)
    candidates = []
    for path, distance in simple_paths(
        graph.adjacency, "start", frozenset(item.node for item in shelters)
    ):
        first_safe = next(
            (index for index, node_id in enumerate(path) if node_id not in hazardous),
            None,
        )
        if first_safe is None:
            continue
        if any(node_id in hazardous for node_id in path[first_safe:]):
            continue
        candidates.append((distance, path[first_safe], path[-1], path))

    expected = min(candidates)
    result = plan_evacuation(case)
    assert result.route is not None
    assert result.route.total_distance == expected[0]
    assert result.route.hazard_exit_node == expected[1]
    assert result.route.shelter_node == expected[2]
    assert result.route.full_path == expected[3]
