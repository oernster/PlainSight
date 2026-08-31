"""Shared machinery for the structural checks: source files and their imports."""

from __future__ import annotations

import ast
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parents[2] / "skillsviewer"
REPOSITORY_ROOT = PACKAGE_ROOT.parent
PACKAGE_NAME = "skillsviewer"

LAYERS = ("domain", "application", "infrastructure", "ui")

# Which layers each layer is allowed to reach. The shape of the invariant:
# UI -> Application -> Domain <- Infrastructure.
PERMITTED_IMPORTS = {
    "domain": frozenset(),
    "application": frozenset({"domain"}),
    "infrastructure": frozenset({"domain", "application"}),
    "ui": frozenset({"domain", "application"}),
}

# Build and packaging scripts are exempt from the size cap: they are linear
# recipes read top to bottom, where splitting a sequence of flags and steps
# across modules costs more than it buys.
BUILD_SCRIPTS = frozenset(
    {
        "buildexe.py",
        "buildinstaller.py",
        "builddmg.py",
        "build_utils.py",
        "dmg_icon.py",
        "generate_icons.py",
        "stamp_version.py",
        "build_payload.py",
    }
)

INSTALLER_ROOT = REPOSITORY_ROOT / "installer"
# The staged bundle lives under the setup program's directory and is build
# output, not source; nothing in it is measured or scanned. Nor is anything in
# a virtual environment, a cache or a dist directory, all of which hold other
# people's code.
BUILD_OUTPUT_PARTS = frozenset(
    {
        "payload",
        "build",
        "__pycache__",
        "node_modules",
        "site-packages",
        "venv",
    }
)
BUILD_OUTPUT_PREFIXES = ("dist", ".")


def is_build_output(path: Path) -> bool:
    """Whether a path sits inside a build output or environment directory."""
    for part in path.parts[:-1]:
        if part in BUILD_OUTPUT_PARTS:
            return True
        if part.startswith(BUILD_OUTPUT_PREFIXES):
            return True
    return False


def source_files(layer: str) -> tuple[Path, ...]:
    """Every Python file in one layer."""
    directory = PACKAGE_ROOT / layer
    if not directory.is_dir():
        return ()
    return tuple(sorted(directory.rglob("*.py")))


def package_files() -> tuple[Path, ...]:
    """Every Python file in the application package."""
    return tuple(sorted(PACKAGE_ROOT.rglob("*.py")))


def parse(path: Path) -> ast.Module:
    """The syntax tree of one source file."""
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def imported_modules(tree: ast.Module, path: Path) -> set[str]:
    """Every module this file imports, with relative imports resolved."""
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            found.add(_resolve(node, path))
    return found


def _resolve(node: ast.ImportFrom, path: Path) -> str:
    """The absolute module name a `from ... import` refers to."""
    if not node.level:
        return node.module or ""
    package_parts = path.relative_to(PACKAGE_ROOT.parent).parts[:-1]
    climbed = package_parts[: len(package_parts) - (node.level - 1)]
    tail = (node.module or "").split(".") if node.module else []
    return ".".join([*climbed, *tail])


def layer_of(module: str) -> str | None:
    """The layer a module name belongs to; None when it is not ours."""
    parts = module.split(".")
    if len(parts) < 2 or parts[0] != PACKAGE_NAME:
        return None
    return parts[1] if parts[1] in LAYERS else None
