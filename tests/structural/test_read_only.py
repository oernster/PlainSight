"""Read only, as an invariant: nothing writes to a document the reader chose.

Editing is the external editor's job, so the application writes only its own
files: the settings file and the release notes it imports, each beneath its own
directory. This test names the modules allowed to write at all and asserts
nothing else calls a writing operation.
"""

from __future__ import annotations

import ast

from .layers import PACKAGE_NAME, package_files, parse

WRITING_CALLS = frozenset(
    {
        "write_text",
        "write_bytes",
        "mkdir",
        "unlink",
        "rmdir",
        "replace",
        "rename",
        "touch",
        "remove",
        "rmtree",
    }
)

# The builtin only. An attribute named `open` is not checked, because a port
# legitimately carries that verb: the external opener asks the desktop to open
# an address and touches no file at all.
WRITING_BUILTINS = frozenset({"open"})

# The modules that write anything. The settings store writes the settings
# file; the collection store writes imported release notes beneath their own
# root; both write through the one atomic writer.
PERMITTED_WRITERS = frozenset(
    {
        f"{PACKAGE_NAME}.infrastructure.settings_store",
        f"{PACKAGE_NAME}.infrastructure.release_collection_store",
        f"{PACKAGE_NAME}.infrastructure.atomic_write",
    }
)


def module_name(path: object) -> str:
    """The dotted module name of a source file inside the package."""
    from .layers import PACKAGE_ROOT

    relative = path.relative_to(PACKAGE_ROOT.parent)  # type: ignore[attr-defined]
    return ".".join(relative.with_suffix("").parts)


def writing_calls(tree: ast.Module) -> set[str]:
    """Every writing operation called anywhere in this file."""
    found: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        target = node.func
        if isinstance(target, ast.Attribute) and target.attr in WRITING_CALLS:
            found.add(target.attr)
        elif isinstance(target, ast.Name) and target.id in WRITING_BUILTINS:
            found.add(target.id)
    return found


def test_only_the_named_writers_write_anything() -> None:
    offences: list[str] = []
    for path in package_files():
        name = module_name(path)
        if name in PERMITTED_WRITERS:
            continue
        calls = writing_calls(parse(path))
        if calls:
            offences.append(f"{name}: {sorted(calls)}")

    assert offences == []
