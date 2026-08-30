from __future__ import annotations

import math

import pytest

from tests.helpers import node
from two_stage_router.graph import Graph, dijkstra
from two_stage_router.model import Edge


def test_dijkstra_finds_shortest_path() -> None:
    graph = Graph(
        (node("a"), node("b"), node("c")),
        (Edge("a", "b", 2), Edge("b", "c", 1), Edge("a", "c", 9)),
    )
    assert dijkstra(graph, "a")["c"].distance == 3
    assert dijkstra(graph, "a")["c"].nodes == ("a", "b", "c")


def test_dijkstra_is_deterministic_on_equal_distances() -> None:
    graph = Graph(
        (node("a"), node("b"), node("c"), node("d")),
        (
            Edge("a", "c", 1),
            Edge("c", "d", 1),
            Edge("a", "b", 1),
            Edge("b", "d", 1),
        ),
    )
    assert dijkstra(graph, "a")["d"].nodes == ("a", "b", "d")


def test_allowed_nodes_remove_shortcut() -> None:
    graph = Graph(
        (node("a"), node("b"), node("c")),
        (Edge("a", "b", 1), Edge("b", "c", 1), Edge("a", "c", 5)),
    )
    result = dijkstra(graph, "a", frozenset({"a", "c"}))
    assert result["c"].distance == 5


def test_disconnected_nodes_are_absent() -> None:
    graph = Graph((node("a"), node("b")), ())
    assert set(dijkstra(graph, "a")) == {"a"}


@pytest.mark.parametrize("weight", [0, -1, math.inf, -math.inf, math.nan, True])
def test_invalid_weights_are_rejected(weight: float) -> None:
    with pytest.raises(ValueError, match="weight"):
        Graph((node("a"), node("b")), (Edge("a", "b", weight),))


def test_empty_graph_is_rejected() -> None:
    with pytest.raises(ValueError, match="at least one"):
        Graph((), ())


def test_duplicate_nodes_are_rejected() -> None:
    with pytest.raises(ValueError, match="unique"):
        Graph((node("a"), node("a")), ())


def test_duplicate_undirected_edges_are_rejected() -> None:
    with pytest.raises(ValueError, match="duplicate edge"):
        Graph(
            (node("a"), node("b")),
            (Edge("a", "b", 1), Edge("b", "a", 1)),
        )


def test_unknown_edge_endpoint_is_rejected() -> None:
    with pytest.raises(ValueError, match="unknown node"):
        Graph((node("a"),), (Edge("a", "missing", 1),))


def test_self_loop_is_rejected() -> None:
    with pytest.raises(ValueError, match="self-loop"):
        Graph((node("a"),), (Edge("a", "a", 1),))


def test_unknown_start_is_rejected() -> None:
    with pytest.raises(ValueError, match="unknown start"):
        dijkstra(Graph((node("a"),), ()), "missing")


def test_start_must_be_allowed() -> None:
    with pytest.raises(ValueError, match="excluded"):
        dijkstra(Graph((node("a"),), ()), "a", frozenset())


def test_unknown_allowed_node_is_rejected() -> None:
    with pytest.raises(ValueError, match="unknown nodes"):
        dijkstra(Graph((node("a"),), ()), "a", frozenset({"a", "missing"}))
