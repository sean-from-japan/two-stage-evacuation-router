"""HTTP adapter that exposes the routing core as a JSON service.

The historical system computed routes on a Flask service and used the Android
client as a graphical shell over it. This adapter reproduces that split without
adding a user interface: the planner stays pure, and the transport layer only
parses a request, delegates, and renders the same document the CLI prints.

Status codes mirror the CLI exit codes. A planned route is ``200``, a valid
scenario with no valid route is ``422``, and malformed input is ``400``.
"""

from __future__ import annotations

import json

from flask import Flask, Response, request
from werkzeug.exceptions import HTTPException

from two_stage_router import __version__
from two_stage_router.io import plan_result_to_json, scenario_from_dict
from two_stage_router.planner import plan_evacuation

JSON_MIMETYPE = "application/json"


def _json(body: str, status: int) -> Response:
    return Response(body, status=status, mimetype=JSON_MIMETYPE)


def _problem(message: str, status: int) -> Response:
    return _json(json.dumps({"error": message}, indent=2, sort_keys=True), status)


def create_app() -> Flask:
    """Build the application. Flask's CLI discovers this factory by name."""

    app = Flask(__name__)

    @app.get("/health")
    def health() -> Response:
        document = json.dumps(
            {"status": "ok", "version": __version__}, indent=2, sort_keys=True
        )
        return _json(document, 200)

    @app.post("/routes")
    def routes() -> Response:
        document = request.get_json(silent=True)
        if not isinstance(document, dict):
            return _problem(
                "request body must be a JSON object sent as application/json", 400
            )
        try:
            result = plan_evacuation(scenario_from_dict(document))
        except ValueError as error:
            return _problem(str(error), 400)
        status = 200 if result.route is not None else 422
        return _json(plan_result_to_json(result), status)

    @app.errorhandler(HTTPException)
    def http_error(error: HTTPException) -> Response:
        return _problem(error.name.lower(), error.code or 500)

    return app
