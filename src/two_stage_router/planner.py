"""Pure two-stage evacuation planning."""

from __future__ import annotations

from dataclasses import replace

from two_stage_router.geometry import project_hazards
from two_stage_router.graph import Graph, dijkstra
from two_stage_router.model import (
    ExitEvaluation,
    PathResult,
    PlanResult,
    Scenario,
    SelectedRoute,
    Shelter,
    ShelterEvaluation,
)


def _validate_scenario(graph: Graph, scenario: Scenario) -> None:
    if scenario.start not in graph.nodes:
        raise ValueError(f"unknown start node: {scenario.start!r}")
    if not scenario.shelters:
        raise ValueError("scenario must contain at least one shelter")
    shelter_ids = {shelter.id for shelter in scenario.shelters}
    if len(shelter_ids) != len(scenario.shelters):
        raise ValueError("shelter ids must be unique")
    for shelter in scenario.shelters:
        if shelter.node not in graph.nodes:
            raise ValueError(
                f"shelter {shelter.id!r} references unknown node {shelter.node!r}"
            )


def _evaluate_shelters(
    graph: Graph,
    exit_node: str,
    shelters: tuple[Shelter, ...],
    hazardous: frozenset[str],
) -> tuple[tuple[ShelterEvaluation, ...], ShelterEvaluation | None]:
    safe_nodes = frozenset(graph.nodes).difference(hazardous)
    paths = dijkstra(graph, exit_node, safe_nodes)
    evaluations: list[ShelterEvaluation] = []
    reachable: list[ShelterEvaluation] = []

    for shelter in sorted(shelters, key=lambda item: item.id):
        if not shelter.eligible:
            evaluation = ShelterEvaluation(
                shelter=shelter.id,
                node=shelter.node,
                status="rejected",
                reason="shelter is marked ineligible",
            )
        elif shelter.node in hazardous:
            evaluation = ShelterEvaluation(
                shelter=shelter.id,
                node=shelter.node,
                status="rejected",
                reason="shelter node is hazardous",
            )
        elif shelter.node not in paths:
            evaluation = ShelterEvaluation(
                shelter=shelter.id,
                node=shelter.node,
                status="unreachable",
                reason="no hazard-free path from this exit",
            )
        else:
            path = paths[shelter.node]
            evaluation = ShelterEvaluation(
                shelter=shelter.id,
                node=shelter.node,
                status="reachable",
                distance=path.distance,
                path=path.nodes,
            )
            reachable.append(evaluation)
        evaluations.append(evaluation)

    if not reachable:
        return tuple(evaluations), None
    best = min(
        reachable,
        key=lambda item: (
            item.distance if item.distance is not None else float("inf"),
            item.shelter,
        ),
    )
    evaluations = [
        replace(item, status="chosen") if item.shelter == best.shelter else item
        for item in evaluations
    ]
    return tuple(evaluations), replace(best, status="chosen")


def plan_evacuation(scenario: Scenario) -> PlanResult:
    """Minimize total distance while preserving the two routing stages.

    Stage one ends at the first safe node. Stage two may use only safe nodes.
    All reachable exits are evaluated before a route is selected, so the nearest
    exit is not chosen greedily when it produces a worse complete route.
    """

    graph = Graph(scenario.nodes, scenario.edges)
    _validate_scenario(graph, scenario)
    hazardous = project_hazards(
        scenario.nodes, scenario.hazards, scenario.hazardous_nodes
    )
    start_in_hazard = scenario.start in hazardous

    if start_in_hazard:
        exits = sorted(
            {
                neighbour
                for node in hazardous
                for neighbour, _weight in graph.neighbours(node)
                if neighbour not in hazardous
            }
        )
        if not exits:
            return PlanResult(
                start=scenario.start,
                start_in_hazard=True,
                hazardous_nodes=tuple(sorted(hazardous)),
                route=None,
                exits=(),
                reason="hazardous component has no adjacent safe exit node",
            )
        hazard_paths = dijkstra(graph, scenario.start, hazardous)
        stage_one_paths: dict[str, PathResult] = {}
        for exit_node in exits:
            approaches = [
                PathResult(
                    distance=hazard_paths[inside].distance + weight,
                    nodes=hazard_paths[inside].nodes + (exit_node,),
                )
                for inside, weight in graph.neighbours(exit_node)
                if inside in hazard_paths
            ]
            if approaches:
                stage_one_paths[exit_node] = min(
                    approaches, key=lambda item: (item.distance, item.nodes)
                )
    else:
        exits = [scenario.start]
        stage_one_paths = dijkstra(graph, scenario.start, frozenset({scenario.start}))

    evaluations: list[ExitEvaluation] = []
    feasible: list[ExitEvaluation] = []
    for exit_node in exits:
        stage_one = stage_one_paths.get(exit_node)
        if stage_one is None:
            evaluations.append(
                ExitEvaluation(
                    exit_node=exit_node,
                    status="unreachable",
                    reason="exit is disconnected from the start inside the hazard",
                )
            )
            continue
        shelters, chosen = _evaluate_shelters(
            graph, exit_node, scenario.shelters, hazardous
        )
        if chosen is None or chosen.distance is None:
            evaluations.append(
                ExitEvaluation(
                    exit_node=exit_node,
                    status="rejected",
                    stage_one_distance=stage_one.distance,
                    stage_one_path=stage_one.nodes,
                    reason="no eligible shelter is reachable without entering a hazard",
                    shelters=shelters,
                )
            )
            continue
        evaluation = ExitEvaluation(
            exit_node=exit_node,
            status="feasible",
            stage_one_distance=stage_one.distance,
            stage_one_path=stage_one.nodes,
            chosen_shelter=chosen.shelter,
            stage_two_distance=chosen.distance,
            stage_two_path=chosen.path,
            total_distance=stage_one.distance + chosen.distance,
            shelters=shelters,
        )
        evaluations.append(evaluation)
        feasible.append(evaluation)

    if not feasible:
        return PlanResult(
            start=scenario.start,
            start_in_hazard=start_in_hazard,
            hazardous_nodes=tuple(sorted(hazardous)),
            route=None,
            exits=tuple(evaluations),
            reason="no complete route can reach an eligible shelter",
        )

    selected = min(
        feasible,
        key=lambda item: (
            item.total_distance if item.total_distance is not None else float("inf"),
            item.stage_one_distance
            if item.stage_one_distance is not None
            else float("inf"),
            item.exit_node,
            item.chosen_shelter or "",
        ),
    )
    evaluations = [
        replace(item, status="selected")
        if item.exit_node == selected.exit_node
        else replace(
            item,
            status="alternative",
            reason="higher complete-route distance than the selected route",
        )
        if item.status == "feasible"
        else item
        for item in evaluations
    ]

    assert selected.stage_one_distance is not None
    assert selected.stage_two_distance is not None
    assert selected.total_distance is not None
    assert selected.chosen_shelter is not None
    shelter = next(
        item for item in scenario.shelters if item.id == selected.chosen_shelter
    )
    full_path = selected.stage_one_path + selected.stage_two_path[1:]
    route = SelectedRoute(
        hazard_exit_node=selected.exit_node,
        shelter=selected.chosen_shelter,
        shelter_node=shelter.node,
        stage_one_distance=selected.stage_one_distance,
        stage_two_distance=selected.stage_two_distance,
        total_distance=selected.total_distance,
        stage_one_path=selected.stage_one_path,
        stage_two_path=selected.stage_two_path,
        full_path=full_path,
    )
    return PlanResult(
        start=scenario.start,
        start_in_hazard=start_in_hazard,
        hazardous_nodes=tuple(sorted(hazardous)),
        route=route,
        exits=tuple(evaluations),
    )
