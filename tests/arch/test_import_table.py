"""Enforce the one-way import table from HANDOFF.md section 5."""

import sys
from pathlib import Path

import pytest

from tests.arch._scan import ImportRef, iter_python_files, scan_file, top_level_module

REPO_ROOT = Path(__file__).resolve().parents[2]
STDLIB = set(sys.stdlib_module_names)


def _paths() -> tuple[Path, ...]:
    return iter_python_files(REPO_ROOT / "src" / "drawgen")


def _group(path: Path) -> tuple[str, set[str]] | None:
    relative = path.relative_to(REPO_ROOT / "src" / "drawgen")
    parts = relative.parts
    if parts == ("__init__.py",) or parts == ("cli.py",):
        return "composition root", set()
    if parts[0] in {"contracts", "core", "packs", "backends", "harness", "assistant"}:
        allowed = {
            "contracts": {"pydantic", "drawgen_shared", "drawgen.contracts"},
            "core": {"drawgen.contracts", "drawgen_shared", "drawgen.core"},
            "packs": {
                "drawgen.core",
                "drawgen.contracts",
                "drawgen_shared",
                "drawgen.packs",
            },
            "backends": {"drawgen.contracts", "drawgen_shared", "drawgen.backends"},
            "harness": {
                "pydantic",
                "langgraph",
                "drawgen.core",
                "drawgen.backends",
                "drawgen.contracts",
                "drawgen_shared",
                "drawgen.harness",
            },
            "assistant": {
                "pydantic",
                "drawgen.core",
                "drawgen.backends",
                "drawgen.contracts",
                "drawgen_shared",
                "drawgen.assistant",
            },
        }[parts[0]]
        return parts[0], allowed
    return None


def _allowed(module: str, group: str, allowed: set[str]) -> bool:
    if top_level_module(module) == "__future__" or top_level_module(module) in STDLIB:
        return True
    if group == "composition root":
        return module == "drawgen" or (
            module.startswith("drawgen.") and not module.startswith("drawgen.packs.")
        )
    return any(module == prefix or module.startswith(prefix + ".") for prefix in allowed)


def _offending(refs: tuple[ImportRef, ...], group_info: tuple[str, set[str]]) -> list[str]:
    group, allowed = group_info
    return [
        f"line {ref.lineno}: {ref.module}"
        for ref in refs
        if not _allowed(ref.module, group, allowed)
    ]


@pytest.mark.parametrize("path", _paths(), ids=lambda path: str(path.relative_to(REPO_ROOT)))
def test_import_table(path: Path) -> None:
    group_info = _group(path)
    assert group_info is not None, f"unknown drawgen package for {path.relative_to(REPO_ROOT)}"
    offending = _offending(scan_file(path, root=REPO_ROOT / "src"), group_info)
    assert not offending, (
        f"{path.relative_to(REPO_ROOT)}: forbidden imports: {', '.join(offending)}"
    )
