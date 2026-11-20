"""Protocol for an interactive NX bridge."""

from __future__ import annotations

from typing import Any, Protocol

from drawgen.contracts.live import (
    ListRequest,
    ListResult,
    LiveMeasureRequest,
    LiveMeasureResults,
    OperationResult,
    Selection,
    SessionContext,
)


class LiveBackendError(Exception):
    """The live bridge could not complete a request."""


class LiveBackend(Protocol):
    def ping(self) -> dict[str, Any]: ...

    def get_context(self) -> SessionContext: ...

    def get_selection(self, include_properties: bool = True) -> Selection: ...

    def measure(self, requests: list[LiveMeasureRequest]) -> LiveMeasureResults: ...

    def list(self, request: ListRequest) -> ListResult: ...

    def execute(self, command: str, inputs: dict[str, Any]) -> OperationResult: ...
