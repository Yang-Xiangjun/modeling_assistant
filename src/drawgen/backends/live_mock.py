"""Scriptable live backend for assistant tests and the first CLI demo."""

from __future__ import annotations

import itertools
from typing import Any

from drawgen.backends.live import LiveBackendError
from drawgen.contracts.live import (
    ListRequest,
    ListResult,
    LiveMeasureRequest,
    LiveMeasureResult,
    LiveMeasureResults,
    OperationResult,
    Selection,
    SessionContext,
)


class MockLiveBackend:
    def __init__(
        self,
        *,
        context: SessionContext | None = None,
        selection: Selection | None = None,
        lists: dict[str, ListResult] | None = None,
        measurements: dict[str, LiveMeasureResult] | None = None,
        supported: frozenset[str] | None = None,
    ) -> None:
        self.supported = supported
        self.context = context or SessionContext(
            work_part={"name": "demo.prt", "path": "C:/demo.prt", "modified": False},
            displayed_part={"name": "demo.prt", "path": "C:/demo.prt", "modified": False},
            application="modeling",
            active_sheet=None,
            active_view="Top",
        )
        self.selection = selection or Selection(items=[])
        self.lists = lists or {}
        self.measurements = measurements or {}
        self.executed: list[tuple[str, dict[str, Any]]] = []
        self.undo_marks: list[str] = []
        self._marks = itertools.count(1)

    def capabilities(self) -> frozenset[str] | None:
        """The scripted session supports every command unless a test restricts it."""

        return self.supported

    def ping(self) -> dict[str, Any]:
        return {"bridge_version": "mock-0", "nx_version": "mock"}

    def get_context(self) -> SessionContext:
        return self.context

    def get_selection(self, include_properties: bool = True) -> Selection:
        if include_properties:
            return self.selection
        return Selection(
            items=[item.model_copy(update={"properties": {}}) for item in self.selection.items]
        )

    def measure(self, requests: list[LiveMeasureRequest]) -> LiveMeasureResults:
        results: list[LiveMeasureResult] = []
        for request in requests:
            result = self.measurements.get(request.id)
            if result is None:
                result = LiveMeasureResult(id=request.id, error="no scripted result")
            results.append(result)
        return LiveMeasureResults(results=results)

    def list(self, request: ListRequest) -> ListResult:
        return self.lists.get(request.what, ListResult(items=[]))

    def execute(self, command: str, inputs: dict[str, Any]) -> OperationResult:
        self.executed.append((command, inputs))
        mark = f"mock-undo-{next(self._marks)}"
        self.undo_marks.append(mark)
        saved = command == "save"
        if command == "fail":
            raise LiveBackendError("scripted live failure")
        return OperationResult(
            command=command,
            undo_mark=mark,
            changed=command
            not in {"open_part", "switch_part", "fit_view", "orient_view", "highlight"},
            saved=saved,
            details={"inputs": inputs},
        )
