"""Subprocess backend for NX's ``run_journal`` batch runner."""

from __future__ import annotations

import os
import subprocess
import time
import uuid
from pathlib import Path
from typing import Any, cast

from drawgen_shared.jsonio import read_json, write_json

from drawgen.backends.base import (
    BackendError,
    WorkerFailed,
    WorkerProtocolError,
    WorkerTimeout,
)
from drawgen.contracts.execution import ExecutionJob, ExecutionReport, ExportedFile
from drawgen.contracts.raw_drawing import RawDrawing
from drawgen.contracts.raw_model import RawModel
from drawgen.contracts.worker import (
    ExportResult,
    MeasureRequest,
    MeasureResult,
    MeasureResults,
    PingResult,
    WorkerJob,
    WorkerStatus,
)


def build_command(run_journal: Path, main_py: Path, job_path: Path) -> list[str]:
    """Build the platform-neutral command line expected by run_journal."""

    return [
        str(run_journal.resolve()),
        str(main_py.resolve()),
        "-args",
        str(job_path.resolve()),
    ]


class NxBackend:
    def __init__(
        self,
        run_journal: Path | None = None,
        repo_root: Path | None = None,
        work_root: Path | None = None,
        timeout_s: float = 600.0,
    ) -> None:
        self.repo_root = (repo_root or Path(__file__).resolve().parents[3]).resolve()
        self.run_journal = self._resolve_run_journal(run_journal)
        self.work_root = (work_root or self.repo_root / "runs" / "nx").resolve()
        self.timeout_s = timeout_s
        self.main_py = self.repo_root / "nx_worker" / "main.py"
        self._last_stdout = ""
        self._last_stderr = ""

    @staticmethod
    def _resolve_run_journal(run_journal: Path | None) -> Path:
        if run_journal is not None:
            return run_journal.expanduser().resolve()
        configured = os.environ.get("DRAWGEN_NX_RUN_JOURNAL")
        if configured:
            return Path(configured).expanduser().resolve()
        base_dir = os.environ.get("UGII_BASE_DIR")
        if base_dir:
            return (Path(base_dir) / "NXBIN" / "run_journal.exe").resolve()
        raise BackendError(
            "NX run_journal executable is not configured; pass run_journal or set "
            "DRAWGEN_NX_RUN_JOURNAL or UGII_BASE_DIR"
        )

    @staticmethod
    def _tail(value: str, limit: int = 4000) -> str:
        return value[-limit:]

    @staticmethod
    def _text(value: str | bytes | None) -> str:
        if value is None:
            return ""
        if isinstance(value, bytes):
            return value.decode(errors="replace")
        return value

    def _new_run_dir(self) -> Path:
        self.work_root.mkdir(parents=True, exist_ok=True)
        while True:
            run_dir = self.work_root / f"{time.strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:10]}"
            try:
                run_dir.mkdir()
            except FileExistsError:
                continue
            return run_dir

    @staticmethod
    def _dump_model(model: Any) -> dict[str, Any]:
        return cast(dict[str, Any], model.model_dump(mode="json", by_alias=True))

    def _run(self, command: str, inputs: dict[str, Any], options: dict[str, Any]) -> dict[str, Any]:
        run_dir = self._new_run_dir()
        job = WorkerJob(command=command, inputs=inputs, output_dir=str(run_dir), options=options)
        job_path = run_dir / "job.json"
        write_json(job_path, self._dump_model(job))
        command_line = build_command(self.run_journal, self.main_py, job_path)
        try:
            completed = subprocess.run(
                command_line,
                capture_output=True,
                text=True,
                timeout=self.timeout_s,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            stdout = self._text(exc.stdout)
            stderr = self._text(exc.stderr)
            raise WorkerTimeout(
                f"NX worker timed out after {self.timeout_s:.3g}s",
                stdout=self._tail(stdout),
                stderr=self._tail(stderr),
            ) from exc
        stdout = self._tail(completed.stdout or "")
        stderr = self._tail(completed.stderr or "")
        self._last_stdout = stdout
        self._last_stderr = stderr
        status_path = run_dir / "status.json"
        if not status_path.is_file():
            raise WorkerProtocolError(
                "worker did not write status.json",
                stdout=stdout,
                stderr=stderr,
            )
        try:
            status = WorkerStatus.model_validate(read_json(status_path))
        except Exception as exc:
            raise WorkerProtocolError(
                f"invalid status.json: {exc}", stdout=stdout, stderr=stderr
            ) from exc
        if not status.ok:
            raise WorkerFailed(status, stdout=stdout, stderr=stderr)
        result_path = run_dir / "result.json"
        if not result_path.is_file():
            raise WorkerProtocolError(
                "worker status is successful but result.json is missing",
                stdout=stdout,
                stderr=stderr,
            )
        try:
            result = read_json(result_path)
        except Exception as exc:
            raise WorkerProtocolError(
                f"invalid result.json: {exc}", stdout=stdout, stderr=stderr
            ) from exc
        if not isinstance(result, dict):
            raise WorkerProtocolError(
                "result.json must contain an object", stdout=stdout, stderr=stderr
            )
        return cast(dict[str, Any], result)

    def _validate_result(
        self,
        model: Any,
        result: dict[str, Any],
        label: str,
    ) -> Any:
        try:
            return model.model_validate(result)
        except Exception as exc:
            raise WorkerProtocolError(
                f"invalid {label}: {exc}", stdout=self._last_stdout, stderr=self._last_stderr
            ) from exc

    def ping(self) -> dict[str, Any]:
        result = cast(
            PingResult,
            self._validate_result(PingResult, self._run("ping", {}, {}), "result.json"),
        )
        return result.model_dump(mode="json")

    def extract_model(self, path: Path) -> RawModel:
        return cast(
            RawModel,
            self._validate_result(
                RawModel, self._run("extract_model", {"part_path": str(path)}, {}), "result.json"
            ),
        )

    def extract_drawing(self, drawing_part_path: Path) -> RawDrawing:
        return cast(
            RawDrawing,
            self._validate_result(
                RawDrawing,
                self._run("extract_drawing", {"drawing_part_path": str(drawing_part_path)}, {}),
                "result.json",
            ),
        )

    def execute_plan(self, job: ExecutionJob) -> ExecutionReport:
        job_dir = self.work_root / "jobs"
        job_dir.mkdir(parents=True, exist_ok=True)
        job_path = job_dir / f"execution-{uuid.uuid4().hex}.json"
        write_json(job_path, self._dump_model(job))
        result = self._run("execute_plan", {"job_path": str(job_path)}, {})
        return cast(ExecutionReport, self._validate_result(ExecutionReport, result, "result.json"))

    def measure(self, part_path: Path, requests: list[MeasureRequest]) -> list[MeasureResult]:
        result = cast(
            MeasureResults,
            self._validate_result(
                MeasureResults,
                self._run(
                    "measure",
                    {
                        "part_path": str(part_path),
                        "requests": [request.model_dump(mode="json") for request in requests],
                    },
                    {},
                ),
                "result.json",
            ),
        )
        return result.results

    def export(
        self, drawing_part_path: Path, formats: list[str], output_dir: Path
    ) -> list[ExportedFile]:
        result = cast(
            ExportResult,
            self._validate_result(
                ExportResult,
                self._run(
                    "export",
                    {
                        "drawing_part_path": str(drawing_part_path),
                        "formats": formats,
                        "output_dir": str(output_dir),
                    },
                    {},
                ),
                "result.json",
            ),
        )
        return result.exports
