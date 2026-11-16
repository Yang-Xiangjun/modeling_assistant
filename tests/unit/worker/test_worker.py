import json
import sys
from pathlib import Path
from typing import Any, cast

import pytest

from nx_worker.main import run_job


def write_job(path: Path, **overrides: object) -> Path:
    job: dict[str, Any] = {
        "protocol": "1",
        "command": "selftest",
        "inputs": {"answer": 42},
        "output_dir": "out",
        "options": {},
    }
    job.update(overrides)
    path.write_text(json.dumps(job), encoding="utf-8")
    return path


def read_status(path: Path) -> dict[str, object]:
    return cast(dict[str, object], json.loads(path.read_text(encoding="utf-8")))


def test_selftest_passes_and_writes_result(tmp_path: Path) -> None:
    job = write_job(tmp_path / "job.json")
    status = run_job(job)
    output = tmp_path / "out"
    assert status["ok"] is True
    assert read_status(output / "status.json")["ok"] is True
    assert json.loads((output / "result.json").read_text(encoding="utf-8")) == {
        "echo": {"answer": 42}
    }


@pytest.mark.parametrize(
    ("name", "job_text", "status_path"),
    [
        ("bad_json", "{", "job.json.status.json"),
        (
            "missing_fields",
            json.dumps({"protocol": "1", "command": "selftest"}),
            "job.json.status.json",
        ),
        (
            "wrong_protocol",
            json.dumps(
                {
                    "protocol": "2",
                    "command": "selftest",
                    "inputs": {},
                    "options": {},
                    "output_dir": "out",
                }
            ),
            "out/status.json",
        ),
        (
            "unknown_command",
            json.dumps(
                {
                    "protocol": "1",
                    "command": "wat",
                    "inputs": {},
                    "options": {},
                    "output_dir": "out",
                }
            ),
            "out/status.json",
        ),
        (
            "not_implemented",
            json.dumps(
                {
                    "protocol": "1",
                    "command": "extract_model",
                    "inputs": {},
                    "options": {},
                    "output_dir": "out",
                }
            ),
            "out/status.json",
        ),
        (
            "command_exception",
            json.dumps(
                {
                    "protocol": "1",
                    "command": "selftest",
                    "inputs": {},
                    "options": {"fail": True},
                    "output_dir": "out",
                }
            ),
            "out/status.json",
        ),
    ],
)
def test_failure_paths_write_status_and_no_result(
    tmp_path: Path, name: str, job_text: str, status_path: str
) -> None:
    del name
    job = tmp_path / "job.json"
    job.write_text(job_text, encoding="utf-8")
    run_job(job)
    status = tmp_path / status_path
    assert status.is_file()
    payload = read_status(status)
    assert payload["ok"] is False
    output_dir = status.parent
    assert not (output_dir / "result.json").exists()


def test_relative_output_dir_resolves_against_job_directory(tmp_path: Path) -> None:
    job_dir = tmp_path / "jobs"
    job_dir.mkdir()
    job = write_job(job_dir / "job.json", output_dir="../runs/relative")
    run_job(job)
    assert (tmp_path / "runs" / "relative" / "status.json").is_file()


def test_ping_with_fake_nxopen(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fake = tmp_path / "NXOpen.py"
    fake.write_text(
        "class Session:\n    @staticmethod\n    def GetSession():\n        return object()\n",
        encoding="utf-8",
    )
    monkeypatch.syspath_prepend(str(tmp_path))
    sys.modules.pop("NXOpen", None)
    job = write_job(tmp_path / "ping.json", command="ping", output_dir="ping-out", inputs={})
    run_job(job)
    status = read_status(tmp_path / "ping-out" / "status.json")
    assert status["ok"] is True
    assert "NXOpen session acquired" in cast(list[str], status["log"])


def test_ping_without_nxopen_is_import_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    sys.modules.pop("NXOpen", None)
    monkeypatch.setattr(sys, "path", [item for item in sys.path if item != str(tmp_path)])
    job = write_job(tmp_path / "ping.json", command="ping", output_dir="ping-out", inputs={})
    run_job(job)
    status = read_status(tmp_path / "ping-out" / "status.json")
    assert status["ok"] is False
    assert status["error"]["type"] == "ModuleNotFoundError"  # type: ignore[index]
