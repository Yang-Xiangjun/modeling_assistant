"""Entry point for journals launched by NX's ``run_journal`` executable.

The worker intentionally uses only the standard library and ``drawgen_shared``
so it can run with the Python bundled with NX.
"""

from __future__ import annotations

import importlib
import os
import platform
import sys
import tempfile
import time
import traceback
from pathlib import Path
from typing import Any


def _repository_paths() -> tuple[Path, Path]:
    # ``__file__`` being set under run_journal is an assumption to confirm in P0-H2.
    entry = globals().get("__file__")
    source = Path(str(entry)) if entry else Path(sys.argv[0])
    worker_root = source.resolve().parent
    repository_root = worker_root.parent
    return repository_root, repository_root / "shared"


_REPOSITORY_ROOT, _SHARED_ROOT = _repository_paths()
for _path in (str(_REPOSITORY_ROOT), str(_SHARED_ROOT)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from drawgen_shared.jsonio import read_json, write_json  # noqa: E402, I001


_KNOWN_COMMANDS = {
    "ping",
    "extract_model",
    "extract_drawing",
    "execute_plan",
    "measure",
    "export",
    "selftest",
}
_NOT_IMPLEMENTED_TASKS = {
    "extract_model": "P1-T1",
    "extract_drawing": "P1-T2",
    "execute_plan": "P2-T4",
    "measure": "P2-T4",
    "export": "P2-T4",
}


def _runtime_status(
    command: str | None,
    *,
    ok: bool,
    duration_s: float,
    error: dict[str, str | None] | None,
    log: list[str],
) -> dict[str, Any]:
    return {
        "ok": ok,
        "command": command,
        "error": error,
        "duration_s": duration_s,
        "nx_version": os.environ.get("UGII_VERSION"),
        "python_version": platform.python_version(),
        "log": log,
    }


def _atomic_write_json(path: Path, obj: Any) -> None:
    """Write JSON through a same-directory temporary file and ``os.replace``."""

    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    os.close(fd)
    temporary = Path(temporary_name)
    try:
        write_json(temporary, obj)
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def _error_payload(exc: BaseException) -> dict[str, str | None]:
    return {
        "type": type(exc).__name__,
        "message": str(exc),
        "traceback": traceback.format_exc(),
    }


def _fallback_status_path(job_path: Path) -> Path:
    return job_path.with_name(f"{job_path.name}.status.json")


def _output_dir_from_job(job_path: Path, raw_job: Any) -> Path | None:
    if not isinstance(raw_job, dict):
        return None
    output_dir = raw_job.get("output_dir")
    if not isinstance(output_dir, str) or not output_dir:
        return None
    candidate = Path(output_dir)
    return candidate if candidate.is_absolute() else job_path.parent / candidate


def _write_status(job_path: Path, output_dir: Path | None, status: dict[str, Any]) -> None:
    status_path = (
        output_dir / "status.json" if output_dir is not None else _fallback_status_path(job_path)
    )
    _atomic_write_json(status_path, status)


def _validate_job(raw_job: Any, job_path: Path) -> tuple[str, dict[str, Any], dict[str, Any], Path]:
    if not isinstance(raw_job, dict):
        raise ValueError("job.json must contain an object")
    required = ("protocol", "command", "inputs", "options", "output_dir")
    missing = [key for key in required if key not in raw_job]
    if missing:
        raise ValueError(f"missing job fields: {', '.join(missing)}")
    if raw_job["protocol"] != "1":
        raise ValueError("unsupported worker protocol; expected '1'")
    command = raw_job["command"]
    if not isinstance(command, str):
        raise ValueError("command must be a string")
    if command not in _KNOWN_COMMANDS:
        raise ValueError(f"unknown command: {command}")
    inputs = raw_job["inputs"]
    options = raw_job["options"]
    if not isinstance(inputs, dict) or not isinstance(options, dict):
        raise ValueError("inputs and options must be objects")
    output_dir = raw_job["output_dir"]
    if not isinstance(output_dir, str) or not output_dir:
        raise ValueError("output_dir must be a non-empty string")
    output_path = Path(output_dir)
    if not output_path.is_absolute():
        output_path = job_path.parent / output_path
    return command, inputs, options, output_path


def run_job(job_path: str | os.PathLike[str]) -> dict[str, Any]:
    """Run one job and return the status dictionary written to disk."""

    path = Path(job_path).resolve()
    started = time.monotonic()
    command: str | None = None
    output_dir: Path | None = None
    log: list[str] = []
    raw_job: Any = None
    try:
        raw_job = read_json(path)
        output_dir = _output_dir_from_job(path, raw_job)
        if isinstance(raw_job, dict) and isinstance(raw_job.get("command"), str):
            command = raw_job["command"]
        command, inputs, options, output_dir = _validate_job(raw_job, path)
        output_dir.mkdir(parents=True, exist_ok=True)
        if command in _NOT_IMPLEMENTED_TASKS:
            task = _NOT_IMPLEMENTED_TASKS[command]
            raise NotImplementedError(f"{command} is implemented by {task}")
        module = importlib.import_module(f"nx_worker.commands.{command}")
        runner = getattr(module, "run")  # noqa: B009
        result = runner(inputs, options, log)
        if not isinstance(result, dict):
            raise TypeError("worker command must return a dictionary")
        _atomic_write_json(output_dir / "result.json", result)
        status = _runtime_status(
            command,
            ok=True,
            duration_s=time.monotonic() - started,
            error=None,
            log=log,
        )
    except BaseException as exc:
        status = _runtime_status(
            command,
            ok=False,
            duration_s=time.monotonic() - started,
            error=_error_payload(exc),
            log=log,
        )
        if output_dir is None:
            output_dir = _output_dir_from_job(path, raw_job)
        if output_dir is not None:
            try:
                output_dir.mkdir(parents=True, exist_ok=True)
                result_path = output_dir / "result.json"
                if result_path.exists():
                    result_path.unlink()
            except OSError:
                output_dir = None
    _write_status(path, output_dir, status)
    return status


def _selftest() -> int:
    import json
    import tempfile

    with tempfile.TemporaryDirectory(prefix="drawgen-worker-selftest-") as directory:
        root = Path(directory)
        passing_dir = root / "passing"
        failing_dir = root / "failing"
        passing_job = root / "passing.json"
        failing_job = root / "failing.json"
        passing_job.write_text(
            json.dumps(
                {
                    "protocol": "1",
                    "command": "selftest",
                    "inputs": {"value": 1},
                    "output_dir": str(passing_dir),
                    "options": {},
                }
            ),
            encoding="utf-8",
        )
        failing_job.write_text(
            json.dumps(
                {
                    "protocol": "1",
                    "command": "selftest",
                    "inputs": {},
                    "output_dir": str(failing_dir),
                    "options": {"fail": True},
                }
            ),
            encoding="utf-8",
        )
        passing = run_job(passing_job)
        failing = run_job(failing_job)
        passing_status = read_json(passing_dir / "status.json")
        failing_status = read_json(failing_dir / "status.json")
        passing_result = (passing_dir / "result.json").exists()
        failing_result = (failing_dir / "result.json").exists()
        passed = (
            passing["ok"]
            and passing_status == passing
            and passing_result
            and not failing["ok"]
            and failing_status == failing
            and not failing_result
        )
        print(f"selftest: {'PASS' if passed else 'FAIL'} (passing and failing jobs)")
        return 0 if passed else 1


def main(argv: list[str] | None = None) -> int:
    """Run a job or the local self-test.

    A normal job returns without ``sys.exit`` because the effect of
    ``SystemExit`` inside NX's journal runner is unverified; status.json is the
    result channel.
    """

    args = list(sys.argv[1:] if argv is None else argv)
    if args == ["--selftest"]:
        return _selftest()
    if len(args) != 1:
        print("usage: main.py <job.json> | --selftest", file=sys.stderr)
        return 2
    run_job(args[0])
    return 0


if __name__ == "__main__":
    _args = sys.argv[1:]
    _code = main(_args)
    # Only the self-test and usage errors call sys.exit.  A normal journal run
    # reaches the end of the module without raising SystemExit.
    if _args == ["--selftest"] or len(_args) != 1:
        sys.exit(_code)
