from __future__ import annotations

import math

import pytest

from tests.helpers import node
from two_stage_router.geometry import contains_or_touches, project_hazards
from two_stage_router.model import Point, Polygon

SQUARE = Polygon("square", (Point(0, 0), Point(2, 0), Point(2, 2), Point(0, 2)))


def test_point_inside_polygon() -> None:
    assert contains_or_touches(SQUARE, Point(1, 1))


def test_point_outside_polygon() -> None:
    assert not contains_or_touches(SQUARE, Point(3, 1))


@pytest.mark.parametrize("point", [Point(1, 0), Point(0, 0), Point(2, 1)])
def test_boundary_is_conservatively_hazardous(point: Point) -> None:
    assert contains_or_touches(SQUARE, point)


def test_concave_polygon() -> None:
    polygon = Polygon(
        "concave",
        (Point(0, 0), Point(3, 0), Point(3, 1), Point(1, 1), Point(1, 3), Point(0, 3)),
    )
    assert contains_or_touches(polygon, Point(0.5, 2))
    assert not contains_or_touches(polygon, Point(2, 2))


def test_project_hazards_unions_polygons_and_explicit_nodes() -> None:
    nodes = (node("inside", 1, 1), node("outside", 3, 3), node("manual", 4, 4))
    assert project_hazards(nodes, (SQUARE,), frozenset({"manual"})) == frozenset(
        {"inside", "manual"}
    )


def test_unknown_explicit_hazard_is_rejected() -> None:
    with pytest.raises(ValueError, match="unknown nodes"):
        project_hazards((node("a"),), (), frozenset({"missing"}))


def test_polygon_needs_three_vertices() -> None:
    polygon = Polygon("line", (Point(0, 0), Point(1, 1)))
    with pytest.raises(ValueError, match="three vertices"):
        contains_or_touches(polygon, Point(0, 0))


def test_polygon_coordinates_must_be_finite() -> None:
    polygon = Polygon("bad", (Point(0, 0), Point(1, 0), Point(math.inf, 1)))
    with pytest.raises(ValueError, match="non-finite"):
        contains_or_touches(polygon, Point(0, 0))
