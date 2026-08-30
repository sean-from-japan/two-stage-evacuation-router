"""Validated road graph and deterministic Dijkstra implementation."""

from __future__ import annotations

import heapq
import math
from collections.abc import Iterable

from two_stage_router.model import Edge, Node, PathResult


class Graph:
    """An immutable, undirected weighted graph."""

    def __init__(self, nodes: Iterable[Node], edges: Iterable[Edge]) -> None:
        node_list = tuple(nodes)
        self.nodes = {node.id: node for node in node_list}
        if not self.nodes:
            raise ValueError("graph must contain at least one node")
        if len(self.nodes) != len(node_list):
            raise ValueError("node ids must be unique")

        adjacency: dict[str, list[tuple[str, float]]] = {
            node_id: [] for node_id in self.nodes
        }
        seen_edges: set[tuple[str, str]] = set()
        for edge in edges:
            if edge.source not in self.nodes or edge.target not in self.nodes:
                raise ValueError(
                    f"edge {edge.source!r}-{edge.target!r} references an unknown node"
                )
            if edge.source == edge.target:
                raise ValueError("self-loop edges are not supported")
            if isinstance(edge.weight, bool) or not math.isfinite(edge.weight):
                raise ValueError("edge weights must be finite numbers")
            if edge.weight <= 0:
                raise ValueError("edge weights must be greater than zero")
            key = (
                (edge.source, edge.target)
                if edge.source < edge.target
                else (edge.target, edge.source)
            )
            if key in seen_edges:
                raise ValueError(f"duplicate edge between {key[0]!r} and {key[1]!r}")
            seen_edges.add(key)
            adjacency[edge.source].append((edge.target, edge.weight))
            adjacency[edge.target].append((edge.source, edge.weight))

        self.adjacency = {
            node: tuple(sorted(neighbours)) for node, neighbours in adjacency.items()
        }

    def neighbours(self, node: str) -> tuple[tuple[str, float], ...]:
        try:
            return self.adjacency[node]
        except KeyError as error:
            raise ValueError(f"unknown node: {node!r}") from error


def dijkstra(
    graph: Graph,
    start: str,
    allowed_nodes: frozenset[str] | None = None,
) -> dict[str, PathResult]:
    """Return shortest paths from ``start`` with deterministic tie handling."""

    if start not in graph.nodes:
        raise ValueError(f"unknown start node: {start!r}")
    allowed = frozenset(graph.nodes) if allowed_nodes is None else allowed_nodes
    if start not in allowed:
        raise ValueError("start node is excluded from the allowed subgraph")
    unknown = allowed.difference(graph.nodes)
    if unknown:
        raise ValueError(f"allowed subgraph contains unknown nodes: {sorted(unknown)}")

    distances = {start: 0.0}
    predecessors: dict[str, str] = {}
    queue: list[tuple[float, str]] = [(0.0, start)]
    settled: set[str] = set()

    while queue:
        distance, node = heapq.heappop(queue)
        if node in settled:
            continue
        settled.add(node)
        for neighbour, weight in graph.neighbours(node):
            if neighbour not in allowed or neighbour in settled:
                continue
            candidate = distance + weight
            current = distances.get(neighbour, math.inf)
            if candidate < current:
                distances[neighbour] = candidate
                predecessors[neighbour] = node
                heapq.heappush(queue, (candidate, neighbour))

    results: dict[str, PathResult] = {}
    for node, distance in distances.items():
        path = [node]
        cursor = node
        while cursor != start:
            cursor = predecessors[cursor]
            path.append(cursor)
        path.reverse()
        results[node] = PathResult(distance=distance, nodes=tuple(path))
    return results
