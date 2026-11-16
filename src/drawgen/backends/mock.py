"""Fixture-backed CAD backend for local and CI runs."""

from __future__ import annotations

import json
import platform
from pathlib import Path
from typing import Any

from drawgen.contracts.execution import ExecutionJob, ExecutionReport, ExportedFile
from drawgen.contracts.raw_drawing import RawDrawing
from drawgen.contracts.raw_model import RawModel
from drawgen.contracts.worker import MeasureRequest, MeasureResult


class MockBackend:
    def __init__(self, fixture_root: Path | None = None) -> None:
        self.fixture_root = fixture_root.resolve() if fixture_root is not None else None

    def _resolve(self, path: Path) -> Path:
        candidate = path
        if not candidate.is_absolute() and self.fixture_root is not None:
            candidate = self.fixture_root / candidate
        return candidate

    def _json_path(self, path: Path, filename: str) -> Path:
        candidate = self._resolve(path)
        if candidate.is_dir():
            candidate = candidate / filename
        return candidate

    @staticmethod
    def _read(path: Path) -> dict[str, Any]:
        with path.open("r", encoding="utf-8") as stream:
            value = json.load(stream)
        if not isinstance(value, dict):
            raise ValueError(f"fixture must contain an object: {path}")
        return value

    def ping(self) -> dict[str, Any]:
        return {
            "backend": "mock",
            "nx_version": None,
            "python_version": platform.python_version(),
        }

    def extract_model(self, path: Path) -> RawModel:
        return RawModel.model_validate(self._read(self._json_path(path, "raw_model.json")))

    def extract_drawing(self, drawing_part_path: Path) -> RawDrawing:
        return RawDrawing.model_validate(
            self._read(self._json_path(drawing_part_path, "raw_drawing.json"))
        )

    def execute_plan(self, job: ExecutionJob) -> ExecutionReport:
        raise NotImplementedError("P2-T5")

    def measure(self, part_path: Path, requests: list[MeasureRequest]) -> list[MeasureResult]:
        raise NotImplementedError("P2-T5")

    def export(
        self, drawing_part_path: Path, formats: list[str], output_dir: Path
    ) -> list[ExportedFile]:
        raise NotImplementedError("P2-T5")
