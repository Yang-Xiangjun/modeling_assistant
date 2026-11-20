import json
import os
import shlex
import stat
import sys
import textwrap
from pathlib import Path

import pytest

from drawgen.backends import get_backend
from drawgen.backends.base import WorkerFailed, WorkerProtocolError, WorkerTimeout
from drawgen.backends.mock import MockBackend
from drawgen.backends.nx import NxBackend, build_command

FIXTURE_SET = Path("fixtures/synthetic/pcba/reference")  # arch: allow-pack-name (fixture path only)


def make_executable(tmp_path: Path, body: str, name: str = "fake.py") -> Path:
    script = tmp_path / name
    script.write_text(textwrap.dedent(body), encoding="utf-8")
    script.chmod(script.stat().st_mode | stat.S_IXUSR)
    if os.name == "nt":
        runner = tmp_path / f"{name}.cmd"
        runner.write_text(
            f'@echo off\n"{sys.executable}" "{script}" %*\n',
            encoding="utf-8",
        )
    else:
        runner = tmp_path / f"{name}.sh"
        runner.write_text(
            f'#!/bin/sh\nexec {shlex.quote(sys.executable)} {shlex.quote(str(script))} "$@"\n',
            encoding="utf-8",
        )
        runner.chmod(runner.stat().st_mode | stat.S_IXUSR)
    return runner


def test_build_command_uses_absolute_paths(tmp_path: Path) -> None:
    command = build_command(Path("runner"), Path("main.py"), tmp_path / "job.json")
    assert command[:3] == [str(Path("runner").resolve()), str(Path("main.py").resolve()), "-args"]
    assert command[3] == str((tmp_path / "job.json").resolve())


def test_mock_backend_reads_reference_fixtures() -> None:
    backend = MockBackend()
    model = backend.extract_model(FIXTURE_SET)
    drawing = backend.extract_drawing(FIXTURE_SET)
    assert model.source.synthetic is True
    assert drawing.source.synthetic is True
    assert backend.ping()["backend"] == "mock"


def test_mock_backend_fixture_root_resolves_relative_paths() -> None:
    backend = MockBackend(FIXTURE_SET.parents[1])
    assert (
        backend.extract_model(FIXTURE_SET.relative_to(FIXTURE_SET.parents[1])).source.synthetic
        is True
    )


def test_get_backend_factory() -> None:
    assert isinstance(get_backend("mock"), MockBackend)
    with pytest.raises(ValueError):
        get_backend("unknown")


def test_nx_ping_round_trip(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    nxopen = tmp_path / "NXOpen.py"
    nxopen.write_text(
        "class Session:\n    @staticmethod\n    def GetSession():\n        return object()\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("PYTHONPATH", str(tmp_path))
    runner = make_executable(
        tmp_path,
        """
        import runpy
        import sys
        main, marker, job = sys.argv[1:4]
        assert marker == '-args'
        sys.argv = [main, job]
        runpy.run_path(main, run_name='__main__')
        """,
        "roundtrip.py",
    )
    backend = NxBackend(run_journal=runner, repo_root=Path.cwd(), work_root=tmp_path / "runs")
    assert backend.ping()["python_version"]


def test_nx_timeout(tmp_path: Path) -> None:
    runner = make_executable(
        tmp_path,
        """
        import time
        time.sleep(2)
        """,
        "sleep.py",
    )
    backend = NxBackend(run_journal=runner, work_root=tmp_path / "runs", timeout_s=0.05)
    with pytest.raises(WorkerTimeout):
        backend.ping()


def test_nx_missing_status(tmp_path: Path) -> None:
    runner = make_executable(tmp_path, "raise SystemExit(0)", "nostatus.py")
    backend = NxBackend(run_journal=runner, work_root=tmp_path / "runs")
    with pytest.raises(WorkerProtocolError, match=r"status\.json"):
        backend.ping()


def test_nx_worker_failed_status(tmp_path: Path) -> None:
    runner = make_executable(
        tmp_path,
        """
        import json
        import pathlib
        import sys
        job = json.loads(pathlib.Path(sys.argv[-1]).read_text())
        out = pathlib.Path(job['output_dir'])
        out.mkdir(parents=True, exist_ok=True)
        (out / 'status.json').write_text(json.dumps({
            'ok': False, 'command': 'ping',
            'error': {'type': 'ValueError', 'message': 'planned failure', 'traceback': None},
            'duration_s': 0.0, 'nx_version': None, 'python_version': '3.12', 'log': []
        }))
        """,
        "failed.py",
    )
    backend = NxBackend(run_journal=runner, work_root=tmp_path / "runs")
    with pytest.raises(WorkerFailed, match="planned failure") as error:
        backend.ping()
    assert error.value.status.error is not None


def test_nx_invalid_result(tmp_path: Path) -> None:
    runner = make_executable(
        tmp_path,
        """
        import json
        import pathlib
        import sys
        job = json.loads(pathlib.Path(sys.argv[-1]).read_text())
        out = pathlib.Path(job['output_dir'])
        out.mkdir(parents=True, exist_ok=True)
        (out / 'status.json').write_text(json.dumps({
            'ok': True, 'command': 'ping', 'error': None, 'duration_s': 0.0,
            'nx_version': None, 'python_version': '3.12', 'log': []
        }))
        (out / 'result.json').write_text('{')
        """,
        "badresult.py",
    )
    backend = NxBackend(run_journal=runner, work_root=tmp_path / "runs")
    with pytest.raises(WorkerProtocolError, match=r"result\.json"):
        backend.ping()


def test_run_journal_resolution_from_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("DRAWGEN_NX_RUN_JOURNAL", raising=False)
    monkeypatch.setenv("UGII_BASE_DIR", str(tmp_path / "nx"))
    backend = NxBackend(work_root=tmp_path / "runs")
    assert backend.run_journal == (tmp_path / "nx" / "NXBIN" / "run_journal.exe").resolve()
    explicit = tmp_path / "explicit"
    monkeypatch.setenv("DRAWGEN_NX_RUN_JOURNAL", str(tmp_path / "env-runner"))
    assert (
        NxBackend(run_journal=explicit, work_root=tmp_path / "runs").run_journal
        == explicit.resolve()
    )


def test_cli_ping_mock(capsys: pytest.CaptureFixture[str]) -> None:
    from drawgen.cli import main

    assert main(["ping", "--backend", "mock"]) == 0
    assert json.loads(capsys.readouterr().out)["backend"] == "mock"


def test_cli_ping_nx_fake(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    nxopen = tmp_path / "NXOpen.py"
    nxopen.write_text(
        "class Session:\n    @staticmethod\n    def GetSession():\n        return object()\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("PYTHONPATH", str(tmp_path))
    runner = make_executable(
        tmp_path,
        """
        import runpy, sys
        main, marker, job = sys.argv[1:4]
        assert marker == '-args'
        sys.argv = [main, job]
        runpy.run_path(main, run_name='__main__')
        """,
        "cli.py",
    )
    from drawgen.cli import main

    assert main(["ping", "--backend", "nx", "--run-journal", str(runner)]) == 0
    assert json.loads(capsys.readouterr().out)["python_version"]
