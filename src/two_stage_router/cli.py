"""Deterministic command-line interface."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from dataclasses import asdict
from pathlib import Path
from typing import Any

from two_stage_router.io import load_scenario
from two_stage_router.model import PlanResult
from two_stage_router.planner import plan_evacuation


def _distance(value: float | None) -> str:
    return "-" if value is None else f"{value:g}"


def format_text(result: PlanResult) -> str:
    lines = [
        "Two-stage evacuation result",
        (
            f"Start: {result.start} "
            f"({'inside' if result.start_in_hazard else 'outside'} hazard)"
        ),
    ]
    if result.route is None:
        lines.append(f"No valid route: {result.reason}")
    else:
        route = result.route
        lines.extend(
            [
                f"Exit: {route.hazard_exit_node}",
                f"Shelter: {route.shelter} ({route.shelter_node})",
                (
                    f"Stage 1: {_distance(route.stage_one_distance)} via "
                    f"{' -> '.join(route.stage_one_path)}"
                ),
                (
                    f"Stage 2: {_distance(route.stage_two_distance)} via "
                    f"{' -> '.join(route.stage_two_path)}"
                ),
                f"Total: {_distance(route.total_distance)}",
            ]
        )
    lines.append("Exit evaluations:")
    if not result.exits:
        lines.append("- none")
    for evaluation in result.exits:
        summary = (
            f"- {evaluation.exit_node}: {evaluation.status}; "
            f"stage1={_distance(evaluation.stage_one_distance)}, "
            f"stage2={_distance(evaluation.stage_two_distance)}, "
            f"total={_distance(evaluation.total_distance)}"
        )
        if evaluation.reason:
            summary += f"; {evaluation.reason}"
        lines.append(summary)
        for shelter in evaluation.shelters:
            detail = (
                f"  - {shelter.shelter}: {shelter.status}; "
                f"distance={_distance(shelter.distance)}"
            )
            if shelter.reason:
                detail += f"; {shelter.reason}"
            lines.append(detail)
    return "\n".join(lines)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="evacuation-route",
        description="Plan a two-stage route on a synthetic road graph.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    plan = subparsers.add_parser("plan", help="plan one scenario")
    plan.add_argument("scenario", type=Path)
    plan.add_argument("--format", choices=("text", "json"), default="text")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = _parser().parse_args(argv)
    try:
        result = plan_evacuation(load_scenario(arguments.scenario))
    except (OSError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 3

    if arguments.format == "json":
        payload: dict[str, Any] = asdict(result)
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(format_text(result))
    return 0 if result.route is not None else 2


if __name__ == "__main__":
    raise SystemExit(main())
