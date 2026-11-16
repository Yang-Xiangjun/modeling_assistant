"""Keep shared helpers and the NX worker free of third-party imports."""

import ast
import sys
from pathlib import Path

import pytest

from tests.arch._scan import ImportRef, iter_python_files, scan_file, top_level_module

REPO_ROOT = Path(__file__).resolve().parents[2]
ALLOWED_ROOTS = {"drawgen_shared", "nx_worker", "nxopen"}
STDLIB = set(sys.stdlib_module_names)


def _all_paths() -> tuple[Path, ...]:
    return iter_python_files(REPO_ROOT / "shared") + iter_python_files(REPO_ROOT / "nx_worker")


def _import_violations(refs: tuple[ImportRef, ...]) -> list[str]:
    violations: list[str] = []
    for ref in refs:
        top_level = top_level_module(ref.module)
        if (
            top_level != "__future__"
            and top_level not in STDLIB
            and top_level.lower() not in ALLOWED_ROOTS
        ):
            violations.append(f"line {ref.lineno}: {ref.module}")
    return violations


@pytest.mark.parametrize("path", _all_paths(), ids=lambda path: str(path.relative_to(REPO_ROOT)))
def test_shared_and_worker_are_python310_and_stdlib_only(path: Path) -> None:
    source = path.read_text(encoding="utf-8")
    try:
        ast.parse(source, filename=str(path), feature_version=(3, 10))
    except SyntaxError as exc:
        pytest.fail(f"{path.relative_to(REPO_ROOT)} uses syntax newer than Python 3.10: {exc}")
    root = REPO_ROOT / "shared" if "shared" in path.relative_to(REPO_ROOT).parts else REPO_ROOT
    violations = _import_violations(scan_file(path, root=root))
    assert not violations, (
        f"{path.relative_to(REPO_ROOT)}: third-party imports: {', '.join(violations)}"
    )
