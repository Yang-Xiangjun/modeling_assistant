"""Keep product-pack names out of generic code and repository metadata."""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
TEXT_SUFFIXES = {".py", ".toml", ".json", ".yaml", ".yml", ".md", ".bat", ".ini"}
MARKER = "arch: allow-pack-name"


SCAN_ROOTS = ("src/drawgen", "shared", "nx_worker", "tests")
EXCLUDED_DIRS = {"__pycache__", ".mypy_cache", ".pytest_cache", ".ruff_cache"}
# Tests that may name a product: generator tests, pack tests, golden tests, and these tests.
EXEMPT_TEST_DIRS = {"tools", "packs", "golden", "arch"}


def _pack_names() -> set[str]:
    names = {"pcba", "housing"}
    packs_root = REPO_ROOT / "src" / "drawgen" / "packs"
    names.update(
        path.name.lower()
        for path in packs_root.iterdir()
        if path.is_dir() and not path.name.startswith(("_", "."))
    )
    return names


def _in_scope(path: Path) -> bool:
    parts = path.relative_to(REPO_ROOT).parts
    if any(part in EXCLUDED_DIRS for part in parts):
        return False
    if parts[:3] == ("src", "drawgen", "packs"):
        return False
    return not (len(parts) >= 2 and parts[0] == "tests" and parts[1] in EXEMPT_TEST_DIRS)


def _name_paths() -> tuple[Path, ...]:
    paths = [
        path for root in SCAN_ROOTS for path in (REPO_ROOT / root).rglob("*") if _in_scope(path)
    ]
    return tuple(sorted(paths))


def _iter_text_files() -> tuple[Path, ...]:
    return tuple(
        path for path in _name_paths() if path.is_file() and path.suffix.lower() in TEXT_SUFFIXES
    )


def test_scope_covers_the_generic_layers() -> None:
    scanned = {path.relative_to(REPO_ROOT).parts[:2] for path in _iter_text_files()}
    for expected in (("src", "drawgen"), ("shared", "drawgen_shared"), ("nx_worker", "main.py")):
        assert expected in scanned


def test_no_pack_names_outside_pack_boundaries() -> None:
    pack_names = _pack_names()
    violations: list[str] = []
    for path in _iter_text_files():
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if MARKER in line:
                continue
            lower_line = line.lower()
            for pack_name in sorted(pack_names):
                if pack_name in lower_line:
                    relative = path.relative_to(REPO_ROOT)
                    violations.append(f"{relative}:{line_number}: {pack_name!r}")
    for path in _name_paths():
        lower_name = path.name.lower()
        for pack_name in sorted(pack_names):
            if pack_name in lower_name:
                violations.append(f"{path.relative_to(REPO_ROOT)} (name contains {pack_name!r})")
    assert not violations, "pack names outside allowed boundaries:\n" + "\n".join(violations)
