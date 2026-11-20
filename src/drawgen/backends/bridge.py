"""Small loopback TCP client for the C# NX bridge."""

from __future__ import annotations

import json
import socket
import uuid
from pathlib import Path
from typing import Any

from drawgen.backends.live import LiveBackendError, LiveBackendTimeout, LiveOutcomeUnknown
from drawgen.contracts.live import (
    BridgeRequest,
    BridgeResponse,
    ListRequest,
    ListResult,
    LiveMeasureRequest,
    LiveMeasureResults,
    OperationResult,
    Selection,
    SessionContext,
)


class BridgeBackend:
    def __init__(
        self, endpoint_file: Path, timeout_s: float = 2.0, change_timeout_s: float = 60.0
    ) -> None:
        self.endpoint_file = endpoint_file.expanduser().resolve()
        self.timeout_s = timeout_s
        # Session and change commands (feature commits, updates) can take far
        # longer than a read; a timeout there leaves the outcome unknown.
        self.change_timeout_s = change_timeout_s

    def _endpoint(self) -> tuple[str, int, str]:
        try:
            payload = json.loads(self.endpoint_file.read_text(encoding="utf-8-sig"))
            return str(payload["host"]), int(payload["port"]), str(payload["token"])
        except (OSError, KeyError, TypeError, ValueError) as exc:
            raise LiveBackendError(f"invalid bridge endpoint: {self.endpoint_file}") from exc

    def _request(
        self,
        command: str,
        inputs: dict[str, Any] | None = None,
        *,
        timeout_s: float | None = None,
    ) -> dict[str, Any]:
        host, port, token = self._endpoint()
        deadline = self.timeout_s if timeout_s is None else timeout_s
        request = BridgeRequest(
            id=uuid.uuid4().hex,
            token=token,
            command=command,
            inputs=inputs or {},
            options={"timeout_s": deadline},
        )
        data = (request.model_dump_json() + "\n").encode("utf-8")
        try:
            with socket.create_connection((host, port), timeout=self.timeout_s) as stream:
                stream.settimeout(deadline)
                stream.sendall(data)
                chunks: list[bytes] = []
                while b"\n" not in b"".join(chunks):
                    chunk = stream.recv(65536)
                    if not chunk:
                        break
                    chunks.append(chunk)
        except TimeoutError as exc:
            raise LiveBackendTimeout(
                f"bridge did not answer '{command}' within {deadline:g} s"
            ) from exc
        except OSError as exc:
            raise LiveBackendError(f"bridge connection failed: {exc}") from exc
        raw = b"".join(chunks).split(b"\n", 1)[0]
        if not raw:
            raise LiveBackendError("bridge returned no response")
        try:
            response = BridgeResponse.model_validate_json(raw)
        except Exception as exc:
            raise LiveBackendError("bridge returned invalid JSON") from exc
        if response.id != request.id:
            raise LiveBackendError("bridge response ID mismatch")
        if not response.status.ok:
            message = (
                response.status.error.message if response.status.error else "bridge command failed"
            )
            raise LiveBackendError(message)
        return response.result or {}

    def ping(self) -> dict[str, Any]:
        return self._request("ping")

    def get_context(self) -> SessionContext:
        return SessionContext.model_validate(self._request("get_context"))

    def get_selection(self, include_properties: bool = True) -> Selection:
        return Selection.model_validate(
            self._request("get_selection", {"include_properties": include_properties})
        )

    def measure(self, requests: list[LiveMeasureRequest]) -> LiveMeasureResults:
        return LiveMeasureResults.model_validate(
            self._request("measure", {"requests": [r.model_dump(mode="json") for r in requests]})
        )

    def list(self, request: ListRequest) -> ListResult:
        return ListResult.model_validate(self._request("list", request.model_dump(mode="json")))

    def execute(self, command: str, inputs: dict[str, Any]) -> OperationResult:
        try:
            payload = self._request(command, inputs, timeout_s=self.change_timeout_s)
        except LiveBackendTimeout as exc:
            raise LiveOutcomeUnknown(
                f"NX did not answer '{command}' within {self.change_timeout_s:g} s, so the "
                "outcome is unknown: it may have been applied. Check NX (use Undo if it ran) "
                "before asking again; the request will not be resent."
            ) from exc
        # Early smoke journals returned operation details directly. Accept that
        # shape while seats still have an older journal loaded, then use the
        # typed operation envelope for all new bridge builds.
        if "command" not in payload and command == "create_box_with_hole":
            payload = {
                "command": command,
                "undo_mark": None,
                "changed": True,
                "saved": bool(payload.get("saved", False)),
                "details": payload,
            }
        return OperationResult.model_validate(payload)
