"""Every third-party package this repository uses is declared somewhere.

Nuitka and Pillow are both used by the delivery scripts. Their predecessor
PyInstaller was used and named in neither requirements file, so a fresh
checkout could run the application and the suite but not build anything. This
test is the reason that cannot happen again.
"""

from __future__ import annotations

import ast
import re
import sys

from .layers import REPOSITORY_ROOT, is_build_output, parse

RUNTIME_REQUIREMENTS = REPOSITORY_ROOT / "requirements.txt"
DEVELOPMENT_REQUIREMENTS = REPOSITORY_ROOT / "requirements-dev.txt"

# Code that belongs to this repository rather than to a package it installs.
FIRST_PARTY = frozenset(
    {
        "plainsight",
        "installer",
        "tests",
        "stamp_version",
        "buildexe",
        "build_utils",
        "dmg_icon",
        "generate_icons",
        "main",
    }
)

# Where an import name and the distribution that provides it differ.
DISTRIBUTION_OF = {
    "PIL": "pillow",
    "docx": "python-docx",
    "pytestqt": "pytest-qt",
    "win32com": "pywin32",
    "pythoncom": "pywin32",
}

# Imported inside a try that falls back when absent, so the build does not
# require them: the shortcut writer drops to a PowerShell script without them.
OPTIONAL = frozenset({"win32com", "pythoncom"})

REQUIREMENT_NAME = re.compile(r"^\s*([A-Za-z0-9._-]+)")

# A tool run as a subprocess is never imported, so the import scan cannot see
# it: the compiler is invoked as `python -m nuitka` and its predecessor was
# missed until a planted removal proved the guard blind to exactly that. These
# are matched in the source text instead.
INVOKED_TOOLS = {
    "nuitka": "nuitka",
}


def declared() -> set[str]:
    """Every distribution named in either requirements file, case folded."""
    return _names(RUNTIME_REQUIREMENTS) | _names(DEVELOPMENT_REQUIREMENTS)


def source_files() -> list:
    """Every Python file in the repository that is source rather than output."""
    return [
        path
        for path in REPOSITORY_ROOT.rglob("*.py")
        if not is_build_output(path) and ".venv" not in path.parts
    ]


def imported_roots(tree: ast.Module) -> set[str]:
    """The top-level name of every module this file imports absolutely."""
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and not node.level and node.module:
            found.add(node.module.split(".")[0])
    return found


def third_party() -> dict[str, set[str]]:
    """Every third-party package used, with the files that use it."""
    used: dict[str, set[str]] = {}
    for path in source_files():
        for root in imported_roots(parse(path)):
            if root in sys.stdlib_module_names or root in FIRST_PARTY:
                continue
            if root in OPTIONAL:
                continue
            used.setdefault(root, set()).add(path.name)
    return used


def invoked() -> dict[str, set[str]]:
    """Every tool run as a subprocess, with the files that run it."""
    used: dict[str, set[str]] = {}
    for path in source_files():
        text = path.read_text(encoding="utf-8")
        for token, distribution in INVOKED_TOOLS.items():
            if f'"{token}"' in text or f"'{token}'" in text:
                used.setdefault(distribution, set()).add(path.name)
    return used


def test_every_package_used_is_declared() -> None:
    named = declared()
    undeclared = {
        package: sorted(files)
        for package, files in third_party().items()
        if DISTRIBUTION_OF.get(package, package).casefold() not in named
    }

    assert undeclared == {}


def test_every_tool_invoked_as_a_subprocess_is_declared() -> None:
    """An import scan cannot see `python -m nuitka`; this can."""
    named = declared()
    undeclared = {
        distribution: sorted(files)
        for distribution, files in invoked().items()
        if distribution.casefold() not in named
    }

    assert undeclared == {}


def test_the_delivery_tools_are_declared_as_development_dependencies() -> None:
    """They build the product; the product itself imports neither.

    Checked against the parsed requirement names rather than the file text: a
    substring check matched the word inside its own explanatory comment, which
    a planted removal caught.
    """
    development = _names(DEVELOPMENT_REQUIREMENTS)
    runtime = _names(RUNTIME_REQUIREMENTS)

    for tool in ("nuitka", "pillow"):
        assert tool in development
        assert tool not in runtime


def _names(path) -> set[str]:
    """The distribution names one requirements file declares."""
    names: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        match = REQUIREMENT_NAME.match(line)
        if match:
            names.add(match.group(1).casefold())
    return names
