from __future__ import annotations

from two_stage_router.model import Edge, Node, Point, Polygon, Scenario, Shelter


def node(node_id: str, x: float = 0, y: float = 0) -> Node:
    return Node(node_id, Point(x, y))


def scenario(
    *,
    nodes: tuple[Node, ...],
    edges: tuple[Edge, ...],
    start: str,
    shelters: tuple[Shelter, ...],
    hazardous: frozenset[str] = frozenset(),
    hazards: tuple[Polygon, ...] = (),
) -> Scenario:
    return Scenario(
        nodes=nodes,
        edges=edges,
        start=start,
        shelters=shelters,
        hazards=hazards,
        hazardous_nodes=hazardous,
    )
