from pathlib import Path

import pytest

from drawgen import __version__
from drawgen.cli import main


def test_cli_without_command_prints_help(capsys: pytest.CaptureFixture[str]) -> None:
    assert main([]) == 0
    assert "drawgen" in capsys.readouterr().out


def test_cli_version(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit):
        main(["--version"])
    assert __version__ in capsys.readouterr().out


def test_live_bridge_missing_endpoint_is_clean_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert (
        main(["live", "ping", "--backend", "bridge", "--endpoint", str(tmp_path / "missing.json")])
        == 1
    )
    assert "invalid bridge endpoint" in capsys.readouterr().err
