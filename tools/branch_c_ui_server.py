"""Local HTTP server for the Branch C browser panel.

The server keeps one in-process assistant session per browser tab, so the
conversation, pending clarification and pending confirmation survive between
messages. A change tool pauses on the exact call it previewed until the page
sends that turn's confirmation ID; nothing is confirmed automatically (rule 8).

Every API call except /api/health must carry the per-launch token that is
embedded in the served page, and POST bodies must be JSON. Other web pages
cannot read the token, so they cannot drive NX through this server.
"""

from __future__ import annotations

import hmac
import json
import os
import secrets
import shutil
import subprocess
import sys
from collections.abc import Mapping
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from drawgen.assistant.agent import AssistantAgent
from drawgen.assistant.log import SessionLog
from drawgen.assistant.session import SessionError, SessionManager
from drawgen.backends.bridge import BridgeBackend
from drawgen.backends.live import LiveBackendError
from drawgen.cli import harness_for, live_backend

ROOT = Path(__file__).resolve().parents[1]
STATIC_FILE = ROOT / "web" / "branch_c_chat.html"
DEFAULT_ENDPOINT = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "drawgen" / "bridge.json"
DEFAULT_PI_AGENT_DIR = ROOT / ".pi-agent"
TOKEN_PLACEHOLDER = "__DRAWGEN_UI_TOKEN__"
TOKEN_HEADER = "X-Drawgen-Token"

Response = tuple[int, dict[str, Any]]


def _nx_running() -> bool:
    if os.name != "nt":
        return False
    result = subprocess.run(
        ["tasklist", "/FI", "IMAGENAME eq ugraf.exe", "/FO", "CSV", "/NH"],
        capture_output=True,
        text=True,
        check=False,
    )
    return "ugraf.exe" in result.stdout.lower()


def _bridge_diagnostic(endpoint: Path) -> tuple[bool, str | None]:
    if not endpoint.exists():
        return False, f"bridge endpoint file not found: {endpoint}"
    try:
        BridgeBackend(endpoint, timeout_s=0.5).ping()
    except LiveBackendError as exc:
        return False, str(exc)
    return True, None


@dataclass
class App:
    backend: str
    harness: str
    endpoint: Path
    token: str = field(default_factory=lambda: secrets.token_urlsafe(32))
    log_root: Path = ROOT / "runs" / "assistant"
    sessions: SessionManager = field(init=False)

    def __post_init__(self) -> None:
        self.sessions = SessionManager(self._agent)

    def _agent(self, session_id: str) -> AssistantAgent:
        endpoint = self.endpoint if self.backend == "bridge" else None
        return AssistantAgent(
            live_backend(self.backend, endpoint),
            harness_for(self.harness),
            log=SessionLog(root=self.log_root, session_id=session_id),
        )

    def page(self) -> bytes:
        return (
            STATIC_FILE.read_text(encoding="utf-8").replace(TOKEN_PLACEHOLDER, self.token).encode()
        )

    def health(self) -> dict[str, Any]:
        pi_command = os.environ.get("DRAWGEN_PI_COMMAND", "pi")
        bridge_ready, bridge_error = (
            _bridge_diagnostic(self.endpoint) if self.backend == "bridge" else (True, None)
        )
        return {
            "nx_running": _nx_running() or (self.backend == "bridge" and bridge_ready),
            "bridge_ready": bridge_ready,
            "bridge_error": bridge_error,
            "bridge_endpoint": str(self.endpoint),
            "pi_command": pi_command,
            "pi_available": self.harness != "pi" or shutil.which(pi_command) is not None,
            "backend": self.backend,
            "harness": self.harness,
        }

    def _authorized(self, headers: Mapping[str, str], *, needs_json: bool) -> Response | None:
        lowered = {key.lower(): value for key, value in headers.items()}
        supplied = lowered.get(TOKEN_HEADER.lower(), "")
        if not hmac.compare_digest(supplied.encode(), self.token.encode()):
            return 403, {"ok": False, "error": "missing or invalid UI token"}
        if needs_json and not lowered.get("content-type", "").startswith("application/json"):
            return 415, {"ok": False, "error": "request body must be application/json"}
        return None

    def handle(
        self, method: str, raw_path: str, headers: Mapping[str, str], body: bytes
    ) -> Response:
        """Route one API request; independent of the HTTP server for testing."""

        url = urlparse(raw_path)
        if method == "GET" and url.path == "/api/health":
            return 200, self.health()
        route = (method, url.path)
        if route not in {("POST", "/api/chat"), ("GET", "/api/turn"), ("POST", "/api/confirm")}:
            return 404, {"ok": False, "error": "Not found"}
        refused = self._authorized(headers, needs_json=method == "POST")
        if refused is not None:
            return refused
        try:
            if method == "GET":
                query = {key: values[0] for key, values in parse_qs(url.query).items()}
                session = self.sessions.get(query.get("session_id", ""))
                return 200, {"ok": True, **session.get_turn(query.get("turn_id", ""))}
            payload = json.loads(body.decode("utf-8") or "{}")
            if not isinstance(payload, dict):
                return 400, {"ok": False, "error": "request body must be a JSON object"}
            session = self.sessions.get(str(payload.get("session_id", "")))
            if url.path == "/api/chat":
                if self.backend == "bridge":
                    ready, error = _bridge_diagnostic(self.endpoint)
                    if not ready:
                        return 503, {
                            "ok": False,
                            "error": (
                                "NX bridge unavailable. Load the Branch C journal in the "
                                f"interactive NX session, then retry. ({error})"
                            ),
                        }
                turn_id = session.start_turn(str(payload.get("message", "")))
                return 202, {"ok": True, "turn_id": turn_id}
            session.resolve_confirmation(
                str(payload.get("turn_id", "")),
                str(payload.get("confirm_id", "")),
                payload.get("approve") is True,
            )
            return 200, {"ok": True}
        except (ValueError, json.JSONDecodeError) as exc:
            return 400, {"ok": False, "error": f"invalid request: {exc}"}
        except SessionError as exc:
            return 409, {"ok": False, "error": str(exc)}


def make_handler(app: App) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        server_version = "BranchCUI/0.2"

        def _send(self, status: int, body: bytes, content_type: str) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _api(self, method: str) -> None:
            length = int(self.headers.get("Content-Length", "0") or "0")
            body = self.rfile.read(length) if length > 0 else b""
            headers = dict(self.headers.items())
            status, payload = app.handle(method, self.path, headers, body)
            encoded = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self._send(status, encoded, "application/json; charset=utf-8")

        def do_GET(self) -> None:
            if urlparse(self.path).path in {"/", "/index.html"}:
                try:
                    self._send(200, app.page(), "text/html; charset=utf-8")
                except OSError as exc:
                    message = json.dumps({"ok": False, "error": str(exc)}).encode()
                    self._send(500, message, "application/json; charset=utf-8")
                return
            self._api("GET")

        def do_POST(self) -> None:
            self._api("POST")

        def log_message(self, format: str, *args: object) -> None:
            print(f"[branch-c-ui] {format % args}", file=sys.stderr)

    return Handler


def main() -> None:
    os.environ.setdefault(
        "PI_CODING_AGENT_DIR", os.environ.get("DRAWGEN_PI_AGENT_DIR", str(DEFAULT_PI_AGENT_DIR))
    )
    app = App(
        backend=os.environ.get("DRAWGEN_UI_BACKEND", "bridge"),
        harness=os.environ.get("DRAWGEN_UI_HARNESS", "pi"),
        endpoint=Path(os.environ.get("DRAWGEN_BRIDGE_ENDPOINT", str(DEFAULT_ENDPOINT))),
    )
    host = "127.0.0.1"
    port = int(os.environ.get("DRAWGEN_UI_PORT", "8765"))
    server = ThreadingHTTPServer((host, port), make_handler(app))
    print(f"Branch C assistant UI listening at http://{host}:{port}")
    print(f"Backend: {app.backend}  Harness: {app.harness}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
