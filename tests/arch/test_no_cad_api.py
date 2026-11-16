"""Enforce CAD API and CAD-library isolation boundaries."""

from pathlib import Path

import pytest

from tests.arch._scan import ImportRef, iter_python_files, scan_file, top_level_module

REPO_ROOT = Path(__file__).resolve().parents[2]
CAD_MODULES = {"occ", "ocp", "freecad", "cadquery", "build123d", "part"}


def _paths() -> tuple[Path, ...]:
    roots = (REPO_ROOT / "src", REPO_ROOT / "shared", REPO_ROOT / "nx_worker", REPO_ROOT / "tools")
    return tuple(path for root in roots for path in iter_python_files(root))


def _violations(path: Path, refs: tuple[ImportRef, ...]) -> list[str]:
    violations: list[str] = []
    relative = path.relative_to(REPO_ROOT)
    for ref in refs:
        module = ref.module.lstrip(".")
        top_level = top_level_module(module)
        if relative.parts[0] in {"src", "shared"} and top_level.lower() == "nxopen":
            violations.append(f"line {ref.lineno}: {ref.module} imports NXOpen")
        if (
            relative.parts[0] == "nx_worker"
            and top_level.lower() == "nxopen"
            and (len(relative.parts) < 3 or relative.parts[1] not in {"commands", "nxutil"})
        ):
            violations.append(
                f"line {ref.lineno}: NXOpen is outside nx_worker/commands or nx_worker/nxutil"
            )
        if relative.parts[0] in {"src", "shared"} and top_level == "nx_worker":
            violations.append(f"line {ref.lineno}: {ref.module} imports nx_worker")
        if top_level.lower() in CAD_MODULES:
            violations.append(f"line {ref.lineno}: {ref.module} imports a CAD library")
    return violations


@pytest.mark.parametrize("path", _paths(), ids=lambda path: str(path.relative_to(REPO_ROOT)))
def test_cad_api_boundaries(path: Path) -> None:
    violations = _violations(path, scan_file(path))
    assert not violations, f"{path.relative_to(REPO_ROOT)}: {'; '.join(violations)}"
