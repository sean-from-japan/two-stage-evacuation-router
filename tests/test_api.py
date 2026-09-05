from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from flask.testing import FlaskClient

from two_stage_router.api import create_app
from two_stage_router.cli import main

ROOT = Path(__file__).resolve().parents[1]
DEMO = ROOT / "examples" / "synthetic_city.json"

TRAPPED = {
    "nodes": [{"id": "a", "x": 0, "y": 0}, {"id": "b", "x": 1, "y": 0}],
    "edges": [{"from": "a", "to": "b", "weight": 1}],
    "start": "a",
    "hazardous_nodes": ["a", "b"],
    "shelters": [{"id": "inside", "node": "b"}],
}


@pytest.fixture
def client() -> FlaskClient:
    return create_app().test_client()


def _post(client: FlaskClient, document: Any) -> Any:
    return client.post("/routes", json=document)


def test_health_reports_the_package_version(client: FlaskClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.mimetype == "application/json"
    assert json.loads(response.data)["status"] == "ok"


def test_route_payload_is_identical_to_the_cli_document(
    client: FlaskClient, capsys: object
) -> None:
    assert main(["plan", str(DEMO), "--format", "json"]) == 0
    expected = capsys.readouterr().out  # type: ignore[attr-defined]

    response = _post(client, json.loads(DEMO.read_text()))

    assert response.status_code == 200
    assert response.data.decode() + "\n" == expected


def test_repeated_requests_return_identical_bytes(client: FlaskClient) -> None:
    document = json.loads(DEMO.read_text())
    first = _post(client, document)
    second = _post(client, document)
    assert first.data == second.data


def test_no_valid_route_is_reported_with_diagnostics(client: FlaskClient) -> None:
    response = _post(client, TRAPPED)
    assert response.status_code == 422
    payload = json.loads(response.data)
    assert payload["route"] is None
    assert payload["reason"] == "hazardous component has no adjacent safe exit node"
    assert payload["hazardous_nodes"] == ["a", "b"]


def test_malformed_document_is_an_input_error(client: FlaskClient) -> None:
    response = _post(client, {"nodes": [], "edges": [], "start": 1, "shelters": []})
    assert response.status_code == 400
    assert "start" in json.loads(response.data)["error"]


def test_invalid_scenario_semantics_are_an_input_error(client: FlaskClient) -> None:
    broken = dict(TRAPPED, edges=[{"from": "a", "to": "b", "weight": -1}])
    response = _post(client, broken)
    assert response.status_code == 400
    assert json.loads(response.data)["error"]


def test_body_must_be_a_json_object(client: FlaskClient) -> None:
    response = _post(client, ["not", "an", "object"])
    assert response.status_code == 400

    raw = client.post("/routes", data="{}", content_type="text/plain")
    assert raw.status_code == 400


def test_transport_errors_are_reported_as_json(client: FlaskClient) -> None:
    wrong_method = client.get("/routes")
    assert wrong_method.status_code == 405
    assert wrong_method.mimetype == "application/json"

    unknown = client.get("/does-not-exist")
    assert unknown.status_code == 404
    assert json.loads(unknown.data)["error"]
