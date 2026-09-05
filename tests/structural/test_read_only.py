"""Read only, as an invariant: nothing writes to a document.

Editing is the external editor's job, so the only writing the
application does is to its own settings file. This test names the one module
allowed to write at all and asserts nothing else calls a writing operation.
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

# The one module that writes anything; it writes only the settings file.
PERMITTED_WRITERS = frozenset({f"{PACKAGE_NAME}.infrastructure.settings_store"})


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


def test_only_the_settings_store_writes_anything() -> None:
    offences: list[str] = []
    for path in package_files():
        name = module_name(path)
        if name in PERMITTED_WRITERS:
            continue
        calls = writing_calls(parse(path))
        if calls:
            offences.append(f"{name}: {sorted(calls)}")

    assert offences == []
