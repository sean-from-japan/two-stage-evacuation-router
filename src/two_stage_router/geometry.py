"""Geometry adapter that projects hazard polygons onto graph nodes."""

from __future__ import annotations

import math

from two_stage_router.model import Node, Point, Polygon


def _on_segment(point: Point, start: Point, end: Point) -> bool:
    cross = (point.y - start.y) * (end.x - start.x) - (point.x - start.x) * (
        end.y - start.y
    )
    if not math.isclose(cross, 0.0, abs_tol=1e-9):
        return False
    return (
        min(start.x, end.x) - 1e-9 <= point.x <= max(start.x, end.x) + 1e-9
        and min(start.y, end.y) - 1e-9 <= point.y <= max(start.y, end.y) + 1e-9
    )


def contains_or_touches(polygon: Polygon, point: Point) -> bool:
    """Return True inside a polygon, treating its boundary as hazardous."""

    if len(polygon.vertices) < 3:
        raise ValueError(f"hazard polygon {polygon.id!r} needs at least three vertices")
    if any(
        not math.isfinite(coordinate)
        for vertex in polygon.vertices
        for coordinate in (vertex.x, vertex.y)
    ):
        raise ValueError(f"hazard polygon {polygon.id!r} has non-finite coordinates")

    inside = False
    previous = polygon.vertices[-1]
    for current in polygon.vertices:
        if _on_segment(point, previous, current):
            return True
        crosses = (current.y > point.y) != (previous.y > point.y)
        if crosses:
            crossing_x = (previous.x - current.x) * (point.y - current.y) / (
                previous.y - current.y
            ) + current.x
            if point.x < crossing_x:
                inside = not inside
        previous = current
    return inside


def project_hazards(
    nodes: tuple[Node, ...],
    polygons: tuple[Polygon, ...],
    explicit_nodes: frozenset[str],
) -> frozenset[str]:
    node_ids = {node.id for node in nodes}
    unknown = explicit_nodes.difference(node_ids)
    if unknown:
        raise ValueError(f"hazard list contains unknown nodes: {sorted(unknown)}")
    projected = set(explicit_nodes)
    for node in nodes:
        if any(contains_or_touches(polygon, node.point) for polygon in polygons):
            projected.add(node.id)
    return frozenset(projected)
