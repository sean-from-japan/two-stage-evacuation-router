from __future__ import annotations

import json
from pathlib import Path

from two_stage_router.cli import main

ROOT = Path(__file__).resolve().parents[1]
DEMO = ROOT / "examples" / "synthetic_city.json"


def test_demo_text_output(capsys: object) -> None:
    assert main(["plan", str(DEMO)]) == 0
    output = capsys.readouterr().out  # type: ignore[attr-defined]
    assert "Exit: exit-far" in output
    assert "Shelter: hill-school (shelter-hill)" in output
    assert "Stage 1: 4 via start -> inner-north -> exit-far" in output
    assert "Stage 2: 2 via exit-far -> shelter-hill" in output
    assert "Total: 6" in output
    assert "exit-near: alternative" in output
    assert "island-hall: unreachable" in output


def test_json_output_is_stable_and_machine_readable(capsys: object) -> None:
    assert main(["plan", str(DEMO), "--format", "json"]) == 0
    first = capsys.readouterr().out  # type: ignore[attr-defined]
    assert main(["plan", str(DEMO), "--format", "json"]) == 0
    second = capsys.readouterr().out  # type: ignore[attr-defined]
    assert first == second
    document = json.loads(first)
    assert document["route"]["hazard_exit_node"] == "exit-far"
    assert document["route"]["total_distance"] == 6


def test_no_route_uses_exit_code_two(tmp_path: Path, capsys: object) -> None:
    document = {
        "nodes": [{"id": "start", "x": 0, "y": 0}, {"id": "s", "x": 1, "y": 0}],
        "edges": [],
        "start": "start",
        "hazardous_nodes": [],
        "shelters": [{"id": "safe", "node": "s"}],
    }
    path = tmp_path / "no-route.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    assert main(["plan", str(path)]) == 2
    output = capsys.readouterr().out  # type: ignore[attr-defined]
    assert "No valid route" in output


def test_invalid_json_uses_exit_code_three(tmp_path: Path, capsys: object) -> None:
    path = tmp_path / "bad.json"
    path.write_text("{", encoding="utf-8")
    assert main(["plan", str(path)]) == 3
    error = capsys.readouterr().err  # type: ignore[attr-defined]
    assert "invalid JSON" in error


def test_missing_file_uses_exit_code_three(tmp_path: Path, capsys: object) -> None:
    assert main(["plan", str(tmp_path / "missing.json")]) == 3
    error = capsys.readouterr().err  # type: ignore[attr-defined]
    assert "error:" in error
