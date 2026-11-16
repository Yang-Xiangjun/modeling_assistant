"""CAD backend protocol and worker errors."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol

from drawgen.contracts.execution import ExecutionJob, ExecutionReport, ExportedFile
from drawgen.contracts.raw_drawing import RawDrawing
from drawgen.contracts.raw_model import RawModel
from drawgen.contracts.worker import MeasureRequest, MeasureResult, WorkerStatus


class BackendError(Exception):
    """A backend could not perform the requested operation."""


class WorkerTimeout(BackendError):
    """The worker process exceeded its configured timeout."""

    def __init__(self, message: str, *, stdout: str = "", stderr: str = "") -> None:
        super().__init__(message)
        self.stdout = stdout
        self.stderr = stderr
        self.stdout_tail = stdout
        self.stderr_tail = stderr


class WorkerProtocolError(BackendError):
    """The worker did not produce valid protocol files."""

    def __init__(self, message: str, *, stdout: str = "", stderr: str = "") -> None:
        super().__init__(message)
        self.stdout = stdout
        self.stderr = stderr
        self.stdout_tail = stdout
        self.stderr_tail = stderr


class WorkerFailed(BackendError):
    """The worker wrote a valid status with ``ok: false``."""

    def __init__(self, status: WorkerStatus, *, stdout: str = "", stderr: str = "") -> None:
        message = status.error.message if status.error is not None else "worker failed"
        super().__init__(message)
        self.status = status
        self.worker_status = status
        self.stdout = stdout
        self.stderr = stderr
        self.stdout_tail = stdout
        self.stderr_tail = stderr


class CadBackend(Protocol):
    def ping(self) -> dict[str, Any]: ...

    def extract_model(self, path: Path) -> RawModel: ...

    def extract_drawing(self, drawing_part_path: Path) -> RawDrawing: ...

    def execute_plan(self, job: ExecutionJob) -> ExecutionReport: ...

    def measure(self, part_path: Path, requests: list[MeasureRequest]) -> list[MeasureResult]: ...

    def export(
        self, drawing_part_path: Path, formats: list[str], output_dir: Path
    ) -> list[ExportedFile]: ...
