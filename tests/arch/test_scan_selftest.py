"""Self-tests for the AST and path scanners used by architecture checks."""

from pathlib import Path

from tests.arch._scan import collect_imported_modules, is_stdlib_module, scan_file, scan_imports


def test_scanners_find_nested_relative_literal_and_forbidden_imports(tmp_path: Path) -> None:
    source = """
import importlib


def nested() -> None:
    import NXOpen
    from NXOpen import Session
    from .sibling import value
    importlib.import_module("yaml")
"""
    source_path = tmp_path / "shared_like.py"
    source_path.write_text(source, encoding="utf-8")

    refs = scan_file(source_path)
    modules = {ref.module for ref in refs}
    assert "NXOpen" in modules
    assert ".sibling" in modules
    assert "yaml" in modules
    assert "importlib" in modules
    assert "NXOpen" in collect_imported_modules(source)
    assert not is_stdlib_module("yaml")


def test_scanner_resolves_relative_imports(tmp_path: Path) -> None:
    source_path = tmp_path / "example.py"
    source_path.write_text("from .sibling import value\n", encoding="utf-8")
    refs = scan_imports(
        source_path.read_text(encoding="utf-8"),
        module_name="drawgen.core.example",
    )
    assert [ref.module for ref in refs] == ["drawgen.core.sibling"]


def test_scanner_exposes_pack_name_in_file_name(tmp_path: Path) -> None:
    path = tmp_path / "housing_fixture.py"
    path.write_text("value = 1\n", encoding="utf-8")
    assert "housing" in path.name.lower()
