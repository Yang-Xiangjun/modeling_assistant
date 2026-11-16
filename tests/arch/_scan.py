"""Small AST scanners shared by architecture tests."""

import ast
import sys
from pathlib import Path


class ImportRef:
    """One import-like reference found in a Python source file."""

    module: str
    level: int
    lineno: int
    col_offset: int
    kind: str

    def __init__(
        self,
        module: str,
        *,
        level: int = 0,
        lineno: int = 0,
        col_offset: int = 0,
        kind: str = "import",
    ) -> None:
        self.module = module
        self.level = level
        self.lineno = lineno
        self.col_offset = col_offset
        self.kind = kind

    def __repr__(self) -> str:
        return f"ImportRef({self.module!r}, line={self.lineno})"


def iter_python_files(root: Path) -> tuple[Path, ...]:
    """Return Python files below *root*, in stable order."""

    return tuple(sorted(root.rglob("*.py")))


def module_name_for_path(path: Path, root: Path) -> tuple[str, bool]:
    """Return the dotted module name and whether *path* is a package init."""

    relative = path.relative_to(root).with_suffix("")
    parts = list(relative.parts)
    is_package = parts[-1] == "__init__"
    if is_package:
        parts.pop()
    return ".".join(parts), is_package


def _resolve_relative(
    module: str,
    level: int,
    current_module: str | None,
    is_package: bool,
) -> str:
    if level == 0 or current_module is None:
        if level == 0:
            return module
        return "." * level + module

    current_parts = current_module.split(".") if current_module else []
    package_parts = current_parts if is_package else current_parts[:-1]
    prefix_length = len(package_parts) - (level - 1)
    if prefix_length < 0:
        return "." * level + module
    resolved_parts = package_parts[:prefix_length]
    if module:
        resolved_parts.append(module)
    return ".".join(resolved_parts)


def scan_imports(
    source: str,
    *,
    module_name: str | None = None,
    is_package: bool = False,
) -> tuple[ImportRef, ...]:
    """Collect imports, including nested imports and literal importlib calls."""

    tree = ast.parse(source)
    refs: list[ImportRef] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                refs.append(
                    ImportRef(
                        alias.name,
                        lineno=node.lineno,
                        col_offset=node.col_offset,
                        kind="import",
                    )
                )
        elif isinstance(node, ast.ImportFrom):
            raw_module = node.module or ""
            refs.append(
                ImportRef(
                    _resolve_relative(raw_module, node.level, module_name, is_package),
                    level=node.level,
                    lineno=node.lineno,
                    col_offset=node.col_offset,
                    kind="from",
                )
            )
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            function = node.func
            if (
                function.attr == "import_module"
                and isinstance(function.value, ast.Name)
                and function.value.id == "importlib"
                and node.args
                and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[0].value, str)
            ):
                refs.append(
                    ImportRef(
                        node.args[0].value,
                        lineno=node.lineno,
                        col_offset=node.col_offset,
                        kind="importlib",
                    )
                )

    refs.sort(key=lambda ref: (ref.lineno, ref.col_offset, ref.module, ref.kind))
    return tuple(refs)


def scan_file(path: Path, *, root: Path | None = None) -> tuple[ImportRef, ...]:
    """Scan a Python file, resolving relative imports when *root* is supplied."""

    source = path.read_text(encoding="utf-8")
    if root is None:
        return scan_imports(source)
    module_name, is_package = module_name_for_path(path, root)
    return scan_imports(source, module_name=module_name, is_package=is_package)


def collect_imported_modules(
    source: str,
    *,
    module_name: str | None = None,
    is_package: bool = False,
) -> tuple[str, ...]:
    """Return imported module names from source, retaining source order."""

    return tuple(
        ref.module for ref in scan_imports(source, module_name=module_name, is_package=is_package)
    )


def collect_imports(
    source: str,
    *,
    module_name: str | None = None,
    is_package: bool = False,
) -> tuple[str, ...]:
    """Compatibility name for collecting imported module names."""

    return collect_imported_modules(source, module_name=module_name, is_package=is_package)


def top_level_module(module: str) -> str:
    """Return the top-level component of a dotted module name."""

    return module.lstrip(".").split(".", 1)[0]


def is_stdlib_module(module: str) -> bool:
    """Whether a module's top-level name is provided by the standard library."""

    return top_level_module(module) in sys.stdlib_module_names
