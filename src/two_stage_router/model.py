"""Domain values shared by the routing core and its adapters."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Point:
    x: float
    y: float


@dataclass(frozen=True)
class Node:
    id: str
    point: Point


@dataclass(frozen=True)
class Edge:
    source: str
    target: str
    weight: float


@dataclass(frozen=True)
class Polygon:
    id: str
    vertices: tuple[Point, ...]


@dataclass(frozen=True)
class Shelter:
    id: str
    node: str
    eligible: bool = True


@dataclass(frozen=True)
class Scenario:
    nodes: tuple[Node, ...]
    edges: tuple[Edge, ...]
    start: str
    shelters: tuple[Shelter, ...]
    hazards: tuple[Polygon, ...] = ()
    hazardous_nodes: frozenset[str] = frozenset()


@dataclass(frozen=True)
class PathResult:
    distance: float
    nodes: tuple[str, ...]


@dataclass(frozen=True)
class ShelterEvaluation:
    shelter: str
    node: str
    status: str
    distance: float | None = None
    path: tuple[str, ...] = ()
    reason: str | None = None


@dataclass(frozen=True)
class ExitEvaluation:
    exit_node: str
    status: str
    stage_one_distance: float | None = None
    stage_one_path: tuple[str, ...] = ()
    chosen_shelter: str | None = None
    stage_two_distance: float | None = None
    stage_two_path: tuple[str, ...] = ()
    total_distance: float | None = None
    reason: str | None = None
    shelters: tuple[ShelterEvaluation, ...] = ()


@dataclass(frozen=True)
class SelectedRoute:
    hazard_exit_node: str
    shelter: str
    shelter_node: str
    stage_one_distance: float
    stage_two_distance: float
    total_distance: float
    stage_one_path: tuple[str, ...]
    stage_two_path: tuple[str, ...]
    full_path: tuple[str, ...]


@dataclass(frozen=True)
class PlanResult:
    start: str
    start_in_hazard: bool
    hazardous_nodes: tuple[str, ...]
    route: SelectedRoute | None
    exits: tuple[ExitEvaluation, ...]
    reason: str | None = None
