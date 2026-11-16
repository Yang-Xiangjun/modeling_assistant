"""Worker protocol messages (HANDOFF.md section 9).

The worker itself reads and writes plain dicts; these models are how the
backends validate them.
"""

from typing import Any, Literal

from pydantic import Field

from drawgen.contracts.common import Contract, Fingerprint, Vec3
from drawgen.contracts.execution import ExportedFile

WorkerCommand = Literal[
    "ping", "extract_model", "extract_drawing", "execute_plan", "measure", "export"
]


class WorkerJob(Contract):
    """job.json"""

    protocol: Literal["1"] = "1"
    command: WorkerCommand
    inputs: dict[str, Any] = Field(default_factory=dict)
    output_dir: str
    options: dict[str, Any] = Field(default_factory=dict)


class WorkerError(Contract):
    type: str
    message: str
    traceback: str | None = None


class WorkerStatus(Contract):
    """status.json: written on every path, including failure."""

    ok: bool
    command: str | None
    error: WorkerError | None = None
    duration_s: float
    nx_version: str | None = None
    python_version: str | None = None
    log: list[str] = Field(default_factory=list)


class PingResult(Contract):
    nx_version: str | None
    python_version: str


class MeasureRequest(Contract):
    id: str
    kind: Literal["distance", "diameter", "angle"]
    a: Fingerprint
    b: Fingerprint | None = None
    direction: Vec3 | None = None


class MeasureResult(Contract):
    id: str
    value: float | None = None
    error: str | None = None


class MeasureResults(Contract):
    results: list[MeasureResult]


class ExportResult(Contract):
    exports: list[ExportedFile]
