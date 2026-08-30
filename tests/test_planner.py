from __future__ import annotations

import pytest

from tests.helpers import node, scenario
from two_stage_router.model import Edge, Point, Polygon, Shelter
from two_stage_router.planner import plan_evacuation


def test_complete_route_beats_greedy_nearest_exit() -> None:
    case = scenario(
        nodes=tuple(node(name) for name in ("start", "h1", "h2", "near", "far", "s")),
        edges=(
            Edge("start", "h1", 1),
            Edge("h1", "near", 1),
            Edge("start", "h2", 2),
            Edge("h2", "far", 2),
            Edge("near", "s", 10),
            Edge("far", "s", 2),
        ),
        start="start",
        shelters=(Shelter("safe", "s"),),
        hazardous=frozenset({"start", "h1", "h2"}),
    )
    result = plan_evacuation(case)
    assert result.route is not None
    assert result.route.hazard_exit_node == "far"
    assert result.route.stage_one_distance == 4
    assert result.route.stage_two_distance == 2
    assert result.route.total_distance == 6
    near = next(item for item in result.exits if item.exit_node == "near")
    assert near.stage_one_distance == 2
    assert near.total_distance == 12
    assert near.status == "alternative"


def test_start_outside_hazard_has_zero_length_first_stage() -> None:
    case = scenario(
        nodes=(node("start"), node("s")),
        edges=(Edge("start", "s", 3),),
        start="start",
        shelters=(Shelter("safe", "s"),),
    )
    result = plan_evacuation(case)
    assert result.route is not None
    assert not result.start_in_hazard
    assert result.route.hazard_exit_node == "start"
    assert result.route.stage_one_distance == 0
    assert result.route.stage_one_path == ("start",)
    assert result.route.full_path == ("start", "s")


def test_start_on_polygon_boundary_counts_as_hazardous() -> None:
    square = Polygon("zone", (Point(0, 0), Point(2, 0), Point(2, 2), Point(0, 2)))
    case = scenario(
        nodes=(node("start", 0, 1), node("exit", -1, 1), node("s", -2, 1)),
        edges=(Edge("start", "exit", 1), Edge("exit", "s", 1)),
        start="start",
        shelters=(Shelter("safe", "s"),),
        hazards=(square,),
    )
    result = plan_evacuation(case)
    assert result.start_in_hazard
    assert result.route is not None
    assert result.route.hazard_exit_node == "exit"


def test_disconnected_exit_is_reported() -> None:
    case = scenario(
        nodes=(node("start"), node("h2"), node("reachable"), node("lost"), node("s")),
        edges=(
            Edge("start", "reachable", 1),
            Edge("h2", "lost", 1),
            Edge("reachable", "s", 1),
        ),
        start="start",
        shelters=(Shelter("safe", "s"),),
        hazardous=frozenset({"start", "h2"}),
    )
    result = plan_evacuation(case)
    lost = next(item for item in result.exits if item.exit_node == "lost")
    assert lost.status == "unreachable"


def test_no_adjacent_safe_exit_returns_explanation() -> None:
    case = scenario(
        nodes=(node("start"), node("h2")),
        edges=(Edge("start", "h2", 1),),
        start="start",
        shelters=(Shelter("unsafe", "h2"),),
        hazardous=frozenset({"start", "h2"}),
    )
    result = plan_evacuation(case)
    assert result.route is None
    assert result.exits == ()
    assert "no adjacent safe exit" in (result.reason or "")


def test_stage_two_cannot_reenter_hazard() -> None:
    case = scenario(
        nodes=(node("start"), node("exit"), node("hazard"), node("detour"), node("s")),
        edges=(
            Edge("start", "exit", 1),
            Edge("exit", "hazard", 1),
            Edge("hazard", "s", 1),
            Edge("exit", "detour", 4),
            Edge("detour", "s", 4),
        ),
        start="start",
        shelters=(Shelter("safe", "s"),),
        hazardous=frozenset({"start", "hazard"}),
    )
    result = plan_evacuation(case)
    assert result.route is not None
    assert result.route.stage_two_path == ("exit", "detour", "s")
    assert result.route.stage_two_distance == 8


def test_ineligible_hazardous_and_unreachable_shelters_are_explained() -> None:
    case = scenario(
        nodes=(
            node("start"),
            node("exit"),
            node("closed"),
            node("unsafe"),
            node("lost"),
        ),
        edges=(
            Edge("start", "exit", 1),
            Edge("exit", "closed", 1),
            Edge("start", "unsafe", 1),
        ),
        start="start",
        shelters=(
            Shelter("closed", "closed", eligible=False),
            Shelter("unsafe", "unsafe"),
            Shelter("lost", "lost"),
        ),
        hazardous=frozenset({"start", "unsafe"}),
    )
    result = plan_evacuation(case)
    assert result.route is None
    evaluation = next(item for item in result.exits if item.exit_node == "exit")
    statuses = {item.shelter: item.status for item in evaluation.shelters}
    assert statuses == {
        "closed": "rejected",
        "lost": "unreachable",
        "unsafe": "rejected",
    }


def test_ties_use_stable_exit_then_shelter_order() -> None:
    case = scenario(
        nodes=(node("start"), node("a"), node("b"), node("s1"), node("s2")),
        edges=(
            Edge("start", "a", 1),
            Edge("start", "b", 1),
            Edge("a", "s1", 2),
            Edge("a", "s2", 2),
            Edge("b", "s1", 2),
        ),
        start="start",
        shelters=(Shelter("z", "s2"), Shelter("a", "s1")),
        hazardous=frozenset({"start"}),
    )
    result = plan_evacuation(case)
    assert result.route is not None
    assert result.route.hazard_exit_node == "a"
    assert result.route.shelter == "a"


def test_explicit_hazardous_nodes_work_without_polygons() -> None:
    case = scenario(
        nodes=(node("start"), node("exit"), node("s")),
        edges=(Edge("start", "exit", 1), Edge("exit", "s", 2)),
        start="start",
        shelters=(Shelter("safe", "s"),),
        hazardous=frozenset({"start"}),
    )
    result = plan_evacuation(case)
    assert result.hazardous_nodes == ("start",)
    assert result.route is not None


def test_multiple_polygons_are_combined() -> None:
    polygons = (
        Polygon("one", (Point(-1, -1), Point(1, -1), Point(1, 1), Point(-1, 1))),
        Polygon("two", (Point(2, -1), Point(4, -1), Point(4, 1), Point(2, 1))),
    )
    case = scenario(
        nodes=(
            node("start", 0, 0),
            node("other", 3, 0),
            node("exit", 5, 0),
            node("s", 6, 0),
        ),
        edges=(
            Edge("start", "other", 1),
            Edge("other", "exit", 1),
            Edge("exit", "s", 1),
        ),
        start="start",
        shelters=(Shelter("safe", "s"),),
        hazards=polygons,
    )
    result = plan_evacuation(case)
    assert result.hazardous_nodes == ("other", "start")
    assert result.route is not None
    assert result.route.hazard_exit_node == "exit"


def test_missing_shelters_is_invalid() -> None:
    case = scenario(nodes=(node("start"),), edges=(), start="start", shelters=())
    with pytest.raises(ValueError, match="at least one shelter"):
        plan_evacuation(case)


def test_duplicate_shelter_ids_are_invalid() -> None:
    case = scenario(
        nodes=(node("start"), node("s")),
        edges=(Edge("start", "s", 1),),
        start="start",
        shelters=(Shelter("same", "start"), Shelter("same", "s")),
    )
    with pytest.raises(ValueError, match="unique"):
        plan_evacuation(case)


def test_unknown_shelter_node_is_invalid() -> None:
    case = scenario(
        nodes=(node("start"),),
        edges=(),
        start="start",
        shelters=(Shelter("bad", "missing"),),
    )
    with pytest.raises(ValueError, match="unknown node"):
        plan_evacuation(case)
