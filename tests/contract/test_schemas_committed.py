"""schemas/ is generated and committed: it must match the pydantic models."""

import json
from pathlib import Path

from tests.conftest import REPO_ROOT
from tools import export_schemas


def test_committed_schemas_are_up_to_date() -> None:
    assert export_schemas.stale() == [], "run `make schemas` and commit the result"


def test_schema_files_are_valid_json_with_titles() -> None:
    files = sorted((REPO_ROOT / "schemas").glob("*.schema.json"))
    assert len(files) == len(export_schemas.render())
    for path in files:
        assert "title" in json.loads(path.read_text())


def test_check_mode_detects_a_stale_directory(tmp_path: Path) -> None:
    assert len(export_schemas.stale(tmp_path)) == len(export_schemas.render())
