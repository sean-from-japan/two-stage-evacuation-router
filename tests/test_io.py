from __future__ import annotations

import pytest

from two_stage_router.io import ScenarioFormatError, scenario_from_dict


def valid_document() -> dict[str, object]:
    return {
        "nodes": [{"id": "a", "x": 0, "y": 0}, {"id": "b", "x": 1, "y": 0}],
        "edges": [{"from": "a", "to": "b", "weight": 1}],
        "start": "a",
        "shelters": [{"id": "safe", "node": "b"}],
        "hazards": [{"id": "zone", "polygon": [[-1, -1], [0, -1], [0, 1]]}],
        "hazardous_nodes": ["a"],
    }


def test_loader_consumes_all_supported_fields() -> None:
    result = scenario_from_dict(valid_document())
    assert result.start == "a"
    assert result.edges[0].weight == 1
    assert result.shelters[0].eligible
    assert result.hazards[0].id == "zone"
    assert result.hazardous_nodes == frozenset({"a"})


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("nodes", {}, "nodes must be an array"),
        ("edges", {}, "edges must be an array"),
        ("start", "", "start must be a non-empty string"),
        ("shelters", {}, "shelters must be an array"),
        ("hazards", {}, "hazards must be an array"),
        ("hazardous_nodes", {}, "hazardous_nodes must be an array"),
    ],
)
def test_top_level_field_shapes_are_checked(
    field: str, value: object, message: str
) -> None:
    document = valid_document()
    document[field] = value
    with pytest.raises(ScenarioFormatError, match=message):
        scenario_from_dict(document)


def test_polygon_point_needs_two_coordinates() -> None:
    document = valid_document()
    document["hazards"] = [{"id": "zone", "polygon": [[0, 1, 2], [1, 2], [2, 0]]}]
    with pytest.raises(ScenarioFormatError, match="exactly x and y"):
        scenario_from_dict(document)


def test_boolean_is_not_an_edge_weight() -> None:
    document = valid_document()
    document["edges"] = [{"from": "a", "to": "b", "weight": True}]
    with pytest.raises(ScenarioFormatError, match="must be a number"):
        scenario_from_dict(document)


def test_eligible_must_be_boolean() -> None:
    document = valid_document()
    document["shelters"] = [{"id": "safe", "node": "b", "eligible": "yes"}]
    with pytest.raises(ScenarioFormatError, match="must be boolean"):
        scenario_from_dict(document)
