"""JSON input adapter for synthetic routing scenarios."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from two_stage_router.model import Edge, Node, Point, Polygon, Scenario, Shelter


class ScenarioFormatError(ValueError):
    """Raised when an input document does not match the consumed schema."""


def _object(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        raise ScenarioFormatError(f"{label} must be an object")
    return value


def _list(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise ScenarioFormatError(f"{label} must be an array")
    return value


def _string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise ScenarioFormatError(f"{label} must be a non-empty string")
    return value


def _number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ScenarioFormatError(f"{label} must be a number")
    return float(value)


def scenario_from_dict(document: Mapping[str, Any]) -> Scenario:
    nodes = []
    for index, raw in enumerate(_list(document.get("nodes"), "nodes")):
        item = _object(raw, f"nodes[{index}]")
        nodes.append(
            Node(
                id=_string(item.get("id"), f"nodes[{index}].id"),
                point=Point(
                    _number(item.get("x"), f"nodes[{index}].x"),
                    _number(item.get("y"), f"nodes[{index}].y"),
                ),
            )
        )

    edges = []
    for index, raw in enumerate(_list(document.get("edges"), "edges")):
        item = _object(raw, f"edges[{index}]")
        edges.append(
            Edge(
                source=_string(item.get("from"), f"edges[{index}].from"),
                target=_string(item.get("to"), f"edges[{index}].to"),
                weight=_number(item.get("weight"), f"edges[{index}].weight"),
            )
        )

    shelters = []
    for index, raw in enumerate(_list(document.get("shelters"), "shelters")):
        item = _object(raw, f"shelters[{index}]")
        eligible = item.get("eligible", True)
        if not isinstance(eligible, bool):
            raise ScenarioFormatError(f"shelters[{index}].eligible must be boolean")
        shelters.append(
            Shelter(
                id=_string(item.get("id"), f"shelters[{index}].id"),
                node=_string(item.get("node"), f"shelters[{index}].node"),
                eligible=eligible,
            )
        )

    hazards = []
    for index, raw in enumerate(_list(document.get("hazards", []), "hazards")):
        item = _object(raw, f"hazards[{index}]")
        vertices = []
        for point_index, raw_point in enumerate(
            _list(item.get("polygon"), f"hazards[{index}].polygon")
        ):
            point = _list(raw_point, f"hazards[{index}].polygon[{point_index}]")
            if len(point) != 2:
                raise ScenarioFormatError("polygon points must contain exactly x and y")
            vertices.append(
                Point(
                    _number(point[0], "polygon x coordinate"),
                    _number(point[1], "polygon y coordinate"),
                )
            )
        hazards.append(
            Polygon(
                id=_string(item.get("id"), f"hazards[{index}].id"),
                vertices=tuple(vertices),
            )
        )

    explicit = frozenset(
        _string(value, "hazardous_nodes item")
        for value in _list(document.get("hazardous_nodes", []), "hazardous_nodes")
    )
    return Scenario(
        nodes=tuple(nodes),
        edges=tuple(edges),
        start=_string(document.get("start"), "start"),
        shelters=tuple(shelters),
        hazards=tuple(hazards),
        hazardous_nodes=explicit,
    )


def load_scenario(path: Path) -> Scenario:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ScenarioFormatError(f"invalid JSON: {error.msg}") from error
    return scenario_from_dict(_object(document, "document"))
