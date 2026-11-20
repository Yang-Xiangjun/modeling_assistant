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


class LiveBackendTimeout(LiveBackendError):
    """The bridge did not answer before the deadline."""


class LiveOutcomeUnknown(LiveBackendTimeout):
    """A session or change command timed out; NX may or may not have applied it.

    The client never replays such a request (HANDOFF 17.2). The user must look
    at NX before asking again.
    """


class LiveBackend(Protocol):
    def ping(self) -> dict[str, Any]: ...

    def get_context(self) -> SessionContext: ...

    def get_selection(self, include_properties: bool = True) -> Selection: ...

    def measure(self, requests: list[LiveMeasureRequest]) -> LiveMeasureResults: ...

    def list(self, request: ListRequest) -> ListResult: ...

    def execute(self, command: str, inputs: dict[str, Any]) -> OperationResult: ...
