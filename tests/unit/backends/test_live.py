import json
import socket
import threading
from pathlib import Path

import pytest

from drawgen.backends.bridge import BridgeBackend
from drawgen.backends.live import LiveBackendError
from drawgen.backends.live_mock import MockLiveBackend
from drawgen.contracts.live import LiveMeasureRequest, LiveMeasureResult, Selection


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
