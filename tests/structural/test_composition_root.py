"""One composition root, with no state built at import time.

Every implementation is constructed in a single place and injected from there.
A module-level instance would be a service locator by another name: reachable
from anywhere, replaceable by nobody.
"""

from __future__ import annotations

import ast

from .layers import PACKAGE_ROOT, package_files, parse

COMPOSITION_ROOT = "__main__.py"

# The concrete implementations. Nothing but the composition root builds one.
IMPLEMENTATIONS = frozenset(
    {
        "FileSystemSkillRepository",
        "JsonSettingsStore",
        "DesktopEditorLauncher",
        "QtExternalOpener",
        "FileSystemPathProbe",
        "HomePlatformPaths",
        "PythonMarkdownRenderer",
        "BundledAssets",
    }
)

# Constructions that are safe at module level because the result cannot change.
IMMUTABLE_CONSTRUCTORS = frozenset({"Palette", "MappingProxyType"})


def constructed_names(tree: ast.Module) -> set[str]:
    """Every class-like name this file calls anywhere."""
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            found.add(node.func.id)
    return found


def module_level_constructions(tree: ast.Module) -> set[str]:
    """Class-like names constructed at import time rather than inside a call."""
    found: set[str] = set()
    for statement in tree.body:
        if not isinstance(statement, ast.Assign):
            continue
        value = statement.value
        if not isinstance(value, ast.Call) or not isinstance(value.func, ast.Name):
            continue
        name = value.func.id
        # Leading underscores are stripped first: a private class name would
        # otherwise slip past the case test, which is how this was found.
        if name.lstrip("_")[:1].isupper() and name not in IMMUTABLE_CONSTRUCTORS:
            found.add(name)
    return found


def test_only_the_composition_root_builds_an_implementation() -> None:
    offences: list[str] = []
    for path in package_files():
        if path.name == COMPOSITION_ROOT and path.parent == PACKAGE_ROOT:
            continue
        built = constructed_names(parse(path)) & IMPLEMENTATIONS
        if built:
            offences.append(f"{path.name}: {sorted(built)}")

    assert offences == []


def test_the_composition_root_builds_every_implementation() -> None:
    """The whitelist cannot go stale: each name is really wired up there."""
    root = parse(PACKAGE_ROOT / COMPOSITION_ROOT)

    assert IMPLEMENTATIONS <= constructed_names(root)


def test_nothing_is_constructed_at_import_time() -> None:
    offences = [
        f"{path.name}: {sorted(names)}"
        for path in package_files()
        if (names := module_level_constructions(parse(path)))
    ]

    assert offences == []
