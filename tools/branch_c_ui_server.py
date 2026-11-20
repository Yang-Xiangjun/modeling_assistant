from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from drawgen.backends.bridge import BridgeBackend
from drawgen.backends.live import LiveBackendError


ROOT = Path(__file__).resolve().parents[1]
STATIC_FILE = ROOT / "web" / "branch_c_chat.html"
DEFAULT_ENDPOINT = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "drawgen" / "bridge.json"
DEFAULT_PI_AGENT_DIR = ROOT / ".pi-agent"


def _env_flag(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


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


def _bridge_reachable(endpoint: Path) -> bool:
    return _bridge_diagnostic(endpoint)[0]


def _health() -> dict[str, object]:
    endpoint = Path(os.environ.get("DRAWGEN_BRIDGE_ENDPOINT", str(DEFAULT_ENDPOINT)))
    pi_command = os.environ.get("DRAWGEN_PI_COMMAND", "pi")
    bridge_ready, bridge_error = _bridge_diagnostic(endpoint)
    return {
        "nx_running": _nx_running() or bridge_ready,
        "bridge_ready": bridge_ready,
        "bridge_error": bridge_error,
        "bridge_endpoint": str(endpoint),
        "pi_command": pi_command,
        "pi_available": shutil.which(pi_command) is not None,
        "backend": os.environ.get("DRAWGEN_UI_BACKEND", "bridge"),
        "dry_run": _env_flag("DRAWGEN_UI_DRY_RUN"),
        "auto_confirm": _env_flag("DRAWGEN_UI_AUTO_CONFIRM", True),
    }


def _chat(message: str) -> tuple[int, dict[str, object]]:
    backend = os.environ.get("DRAWGEN_UI_BACKEND", "bridge")
    endpoint = Path(os.environ.get("DRAWGEN_BRIDGE_ENDPOINT", str(DEFAULT_ENDPOINT)))
    command = [
        "uv",
        "run",
        "drawgen",
        "assistant",
        "chat",
        "--backend",
        backend,
        "--harness",
        "pi",
        "--message",
        message,
    ]
    if backend == "bridge":
        command.extend(["--endpoint", str(endpoint)])
        bridge_ready, bridge_error = _bridge_diagnostic(endpoint)
        if not bridge_ready:
            return 503, {
                "ok": False,
                "error": (
                    "NX bridge unavailable. Load the Branch C journal or compiled bridge "
                    f"in the interactive NX session, then retry. ({bridge_error})"
                ),
            }
    if _env_flag("DRAWGEN_UI_AUTO_CONFIRM", True):
        command.append("--yes")

    try:
        completed = subprocess.run(
            command,
            cwd=ROOT,
            env={
                **os.environ,
                "UV_CACHE_DIR": str(ROOT / ".uv-cache"),
                "PI_CODING_AGENT_DIR": os.environ.get(
                    "DRAWGEN_PI_AGENT_DIR", str(DEFAULT_PI_AGENT_DIR)
                ),
            },
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=180,
            check=False,
        )
    except FileNotFoundError as exc:
        return 503, {"ok": False, "error": f"Unable to start the chat command: {exc}"}
    except subprocess.TimeoutExpired:
        return 504, {"ok": False, "error": "The chat command timed out after 180 seconds."}

    output = completed.stdout.strip()
    error = completed.stderr.strip()
    if completed.returncode != 0:
        detail = error or output or f"chat command exited with code {completed.returncode}"
        return 500, {"ok": False, "error": detail}
    return 200, {"ok": True, "answer": output, "stderr": error}


class Handler(BaseHTTPRequestHandler):
    server_version = "BranchCUI/0.1"

    def _write_json(self, status: int, payload: dict[str, object]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path == "/api/health":
            self._write_json(200, _health())
            return
        if path in {"/", "/index.html"}:
            try:
                body = STATIC_FILE.read_bytes()
            except OSError as exc:
                self._write_json(500, {"ok": False, "error": str(exc)})
                return
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        self._write_json(404, {"ok": False, "error": "Not found"})

    def do_POST(self) -> None:  # noqa: N802
        if urlparse(self.path).path != "/api/chat":
            self._write_json(404, {"ok": False, "error": "Not found"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            message = str(payload.get("message", "")).strip()
        except (ValueError, json.JSONDecodeError) as exc:
            self._write_json(400, {"ok": False, "error": f"Invalid request: {exc}"})
            return
        if not message:
            self._write_json(400, {"ok": False, "error": "Message is required."})
            return
        status, result = _chat(message)
        self._write_json(status, result)

    def log_message(self, format: str, *args: object) -> None:
        print(f"[branch-c-ui] {format % args}", file=sys.stderr)


def main() -> None:
    host = os.environ.get("DRAWGEN_UI_HOST", "127.0.0.1")
    port = int(os.environ.get("DRAWGEN_UI_PORT", "8765"))
    server = ThreadingHTTPServer((host, port), Handler)
    print(f"Branch C assistant UI listening at http://{host}:{port}")
    print(f"Backend: {os.environ.get('DRAWGEN_UI_BACKEND', 'bridge')}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
