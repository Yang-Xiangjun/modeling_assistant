import json
import socket
import threading
from pathlib import Path

import pytest

from drawgen.backends.bridge import LEGACY_BRIDGE_COMMANDS, BridgeBackend
from drawgen.backends.live import LiveBackendError, LiveBackendTimeout, LiveOutcomeUnknown
from drawgen.backends.live_mock import MockLiveBackend
from drawgen.contracts.live import LiveMeasureRequest, LiveMeasureResult, Selection


def _silent_bridge(tmp_path: Path) -> tuple[Path, list[str], threading.Event]:
    """A bridge that reads requests and never answers, like a stalled NX."""

    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.bind(("127.0.0.1", 0))
    listener.listen(4)
    received: list[str] = []
    stop = threading.Event()

    def serve() -> None:
        listener.settimeout(0.1)
        open_connections = []
        while not stop.is_set():
            try:
                connection, _ = listener.accept()
            except TimeoutError:
                continue
            open_connections.append(connection)
            received.append(json.loads(connection.recv(4096).decode("utf-8"))["command"])
        for connection in open_connections:
            connection.close()
        listener.close()

    threading.Thread(target=serve, daemon=True).start()
    endpoint = tmp_path / "bridge.json"
    port = listener.getsockname()[1]
    endpoint.write_text(json.dumps({"host": "127.0.0.1", "port": port, "token": "t"}))
    return endpoint, received, stop


def test_read_timeout_is_a_plain_timeout(tmp_path: Path) -> None:
    endpoint, _received, stop = _silent_bridge(tmp_path)
    try:
        with pytest.raises(LiveBackendTimeout) as caught:
            BridgeBackend(endpoint, timeout_s=0.2).get_selection()
        assert not isinstance(caught.value, LiveOutcomeUnknown)
    finally:
        stop.set()


def test_change_timeout_reports_unknown_outcome_and_is_not_resent(tmp_path: Path) -> None:
    endpoint, received, stop = _silent_bridge(tmp_path)
    try:
        backend = BridgeBackend(endpoint, timeout_s=0.2, change_timeout_s=0.2)
        with pytest.raises(LiveOutcomeUnknown, match="outcome is unknown"):
            backend.execute("hide_entity", {"handle": "tag:1"})
        assert received == ["hide_entity"]
    finally:
        stop.set()


def test_mock_live_ping_and_empty_selection() -> None:
    backend = MockLiveBackend()
    assert backend.ping()["bridge_version"] == "mock-0"
    assert backend.get_selection().items == []


def test_mock_live_supports_typed_volume_measurement() -> None:
    backend = MockLiveBackend(
        measurements={
            "volume-0": LiveMeasureResult(id="volume-0", value=120000.0, unit="mm3"),
        }
    )

    results = backend.measure([LiveMeasureRequest(id="volume-0", kind="volume", a="body:0")])

    assert results.results[0].value == 120000.0
    assert results.results[0].unit == "mm3"
    assert results.results[0].error is None


def test_bridge_rejects_missing_endpoint(tmp_path: Path) -> None:
    with pytest.raises(LiveBackendError, match="invalid bridge endpoint"):
        BridgeBackend(tmp_path / "missing.json").ping()


def test_bridge_round_trip_with_fake_server(tmp_path: Path) -> None:
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.bind(("127.0.0.1", 0))
    listener.listen(1)
    port = listener.getsockname()[1]

    def serve() -> None:
        connection, _ = listener.accept()
        with connection:
            request = json.loads(connection.recv(4096).decode("utf-8"))
            response = {
                "id": request["id"],
                "status": {
                    "ok": True,
                    "command": request["command"],
                    "error": None,
                    "duration_s": 0.001,
                    "nx_version": "mock",
                    "python_version": None,
                    "log": [],
                },
                "result": {"schema": "selection/0", "items": []},
            }
            connection.sendall((json.dumps(response) + "\n").encode("utf-8"))
        listener.close()

    thread = threading.Thread(target=serve, daemon=True)
    thread.start()
    endpoint = tmp_path / "bridge.json"
    endpoint.write_text(json.dumps({"host": "127.0.0.1", "port": port, "token": "t"}))
    selection = BridgeBackend(endpoint).get_selection()
    thread.join(timeout=2)
    assert isinstance(selection, Selection)
    assert selection.items == []


def _answer_once(tmp_path: Path, result: object, error: str | None) -> Path:
    """A bridge that answers one request with a result or an error status."""

    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.bind(("127.0.0.1", 0))
    listener.listen(1)

    def serve() -> None:
        connection, _ = listener.accept()
        with connection:
            request = json.loads(connection.recv(4096).decode("utf-8"))
            status = {
                "ok": error is None,
                "command": request["command"],
                "error": None if error is None else {"type": "NotSupported", "message": error},
                "duration_s": 0.0,
                "nx_version": "mock",
                "python_version": None,
                "log": [],
            }
            response = {"id": request["id"], "status": status, "result": result}
            connection.sendall((json.dumps(response) + "\n").encode("utf-8"))
        listener.close()

    threading.Thread(target=serve, daemon=True).start()
    endpoint = tmp_path / "bridge.json"
    port = listener.getsockname()[1]
    endpoint.write_text(json.dumps({"host": "127.0.0.1", "port": port, "token": "t"}))
    return endpoint


def test_older_bridge_without_capabilities_uses_the_known_command_set(tmp_path: Path) -> None:
    endpoint = _answer_once(tmp_path, None, "unsupported NX command 'capabilities'")
    assert BridgeBackend(endpoint).capabilities() == LEGACY_BRIDGE_COMMANDS


def test_bridge_capabilities_answer_is_used(tmp_path: Path) -> None:
    endpoint = _answer_once(tmp_path, {"commands": ["get_selection", "measure"]}, None)
    assert BridgeBackend(endpoint).capabilities() == frozenset({"get_selection", "measure"})
