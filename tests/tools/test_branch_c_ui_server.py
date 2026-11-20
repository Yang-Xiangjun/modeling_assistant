"""Browser UI server: token gate, JSON-only POSTs, confirm flow over the API."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from drawgen.backends.live_mock import MockLiveBackend
from tools import branch_c_ui_server as ui


def _app(tmp_path: Path) -> ui.App:
    return ui.App(
        backend="mock",
        harness="fake",
        endpoint=tmp_path / "bridge.json",
        token="test-token",
        log_root=tmp_path / "logs",
    )


def _post(
    app: ui.App, path: str, body: dict[str, Any], **headers: str
) -> tuple[int, dict[str, Any]]:
    sent = {"X-Drawgen-Token": "test-token", "Content-Type": "application/json", **headers}
    return app.handle("POST", path, sent, json.dumps(body).encode())


def _turn(app: ui.App, session_id: str, turn_id: str) -> dict[str, Any]:
    query = f"/api/turn?session_id={session_id}&turn_id={turn_id}"
    deadline = time.monotonic() + 5
    while True:
        status, payload = app.handle("GET", query, {"x-drawgen-token": "test-token"}, b"")
        assert status == 200
        if payload["status"] != "running" or time.monotonic() > deadline:
            return payload
        time.sleep(0.01)


def test_api_requires_the_launch_token(tmp_path: Path) -> None:
    app = _app(tmp_path)
    status, _ = app.handle(
        "POST",
        "/api/chat",
        {"Content-Type": "application/json"},
        b'{"session_id": "session-0001", "message": "hi"}',
    )
    assert status == 403
    status, _ = _post(app, "/api/chat", {}, **{"X-Drawgen-Token": "wrong"})
    assert status == 403


def test_post_must_be_json(tmp_path: Path) -> None:
    app = _app(tmp_path)
    status, _ = app.handle(
        "POST",
        "/api/chat",
        {"X-Drawgen-Token": "test-token", "Content-Type": "text/plain"},
        b'{"session_id": "session-0001", "message": "hi"}',
    )
    assert status == 415


def test_health_needs_no_token_and_page_embeds_it(tmp_path: Path) -> None:
    app = _app(tmp_path)
    status, payload = app.handle("GET", "/api/health", {}, b"")
    assert status == 200
    assert payload["backend"] == "mock"
    assert b"test-token" in app.page()


def test_change_runs_only_after_confirm_through_the_api(tmp_path: Path) -> None:
    app = _app(tmp_path)
    session_id = "session-0001"
    status, started = _post(
        app,
        "/api/chat",
        {"session_id": session_id, "message": "Create a 100 x 60 x 20 box with a 10 mm hole"},
    )
    assert status == 202
    paused = _turn(app, session_id, started["turn_id"])
    assert paused["status"] == "needs_confirmation"

    backend = app.sessions.get(session_id).agent.backend
    assert isinstance(backend, MockLiveBackend)
    assert backend.executed == []

    status, _ = _post(
        app,
        "/api/confirm",
        {
            "session_id": session_id,
            "turn_id": started["turn_id"],
            "confirm_id": paused["confirm_id"],
            "approve": True,
        },
    )
    assert status == 200
    done = _turn(app, session_id, started["turn_id"])
    assert done["status"] == "done"
    assert [command for command, _ in backend.executed] == ["create_box_with_hole"]


def test_unknown_routes_and_bad_sessions(tmp_path: Path) -> None:
    app = _app(tmp_path)
    assert app.handle("GET", "/api/nothing", {}, b"")[0] == 404
    status, _ = _post(app, "/api/chat", {"session_id": "x", "message": "hi"})
    assert status == 409
