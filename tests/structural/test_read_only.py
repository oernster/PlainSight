"""Read only, as an allowlist: each module may use only the writes granted to it.

Editing is the external editor's job, so the application writes only its own
files: the settings file and the release notes it imports, each beneath its own
directory. Every write capability a module uses (see ``write_capabilities``)
must be granted to it by name below; anything ungranted fails, in any module,
the new ones included. A grant is the place a reason is written down.

It is a check on this package's source. What it reads and what it cannot see
are stated in ``write_capabilities``.
"""

from __future__ import annotations

from collections.abc import Mapping

from .layers import PACKAGE_NAME, package_files, parse
from .write_capabilities import writing_calls

__all__ = ["writing_calls"]

INFRASTRUCTURE = f"{PACKAGE_NAME}.infrastructure"

# Module, then exactly what it may use, each with its reason.
GRANTS: Mapping[str, frozenset[str]] = {
    # The one home of the temporary file, the flush and the replace.
    f"{INFRASTRUCTURE}.atomic_write": frozenset(
        {"import tempfile", "mkstemp", "write", "replace", "unlink"}
    ),
    # Writes the settings file through the atomic writer; makes its folder.
    f"{INFRASTRUCTURE}.settings_store": frozenset({"mkdir"}),
    # Writes imported release notes beneath their own root and only there. A
    # refresh goes through the atomic writer; a first import builds the whole
    # collection in a temporary folder beside it, then renames it into place.
    f"{INFRASTRUCTURE}.release_collection_store": frozenset(
        {
            "import shutil",
            "import tempfile",
            "mkdir",
            "mkdtemp",
            "write_bytes",
            "rename",
            "rmtree",
        }
    ),
    # Starts the reader's chosen editor on the document; writes nothing itself.
    f"{INFRASTRUCTURE}.desktop": frozenset({"import QProcess", "QProcess"}),
    # Calls the settings store's port, named ``save``; QImage's write shares
    # the name, so the call is granted here rather than the name ignored.
    f"{PACKAGE_NAME}.application.services": frozenset({"save"}),
}


def module_name(path: object) -> str:
    """The dotted module name of a source file inside the package."""
    from .layers import PACKAGE_ROOT

    relative = path.relative_to(PACKAGE_ROOT.parent)  # type: ignore[attr-defined]
    return ".".join(relative.with_suffix("").parts)


def capabilities_by_module() -> dict[str, set[str]]:
    """Every module in the package and the write capabilities it uses."""
    return {module_name(path): writing_calls(parse(path)) for path in package_files()}


def test_no_module_writes_beyond_its_grant() -> None:
    offences = [
        f"{name}: {sorted(used - GRANTS.get(name, frozenset()))}"
        for name, used in capabilities_by_module().items()
        if used - GRANTS.get(name, frozenset())
    ]

    assert offences == []


def test_every_grant_is_still_used() -> None:
    """A grant nothing uses is a door left open for the next change."""
    used = capabilities_by_module()
    stale = [
        f"{name}: {sorted(granted - used.get(name, set()))}"
        for name, granted in GRANTS.items()
        if granted - used.get(name, set())
    ]

    assert stale == []
