"""Every dependency the project declares is credited in About.

Design plan 5.2 says About names every real dependency with its licence. That
was true when it was written and had quietly stopped being true: the packaging
toolchain was credited nowhere at all; three of the gates hid behind the name
of a fourth. Nothing caught it, because a credit list is prose until
something compares it with the requirements files.

This does not check the licence text. A licence is read from the installed
package's own metadata by a person; two of them were wrong from memory. Pillow
moved from HPND to MIT-CMU; Nuitka is AGPL-3.0 with a runtime exception rather
than the Apache-2.0 it once carried. What this holds is the
weaker, checkable half: nothing declared may go unmentioned.
"""

from __future__ import annotations

import re

from skillsviewer.ui.about_dialog import CREDITS

from .layers import REPOSITORY_ROOT

RUNTIME_REQUIREMENTS = REPOSITORY_ROOT / "requirements.txt"
DEVELOPMENT_REQUIREMENTS = REPOSITORY_ROOT / "requirements-dev.txt"

REQUIREMENT_NAME = re.compile(r"^\s*([A-Za-z0-9._-]+)")

# Named in the credits under a name of its own rather than the distribution's.
SPELLED_DIFFERENTLY = {"pillow": "Pillow"}


def declared() -> set[str]:
    """Every distribution either requirements file names, case folded."""
    found: set[str] = set()
    for path in (RUNTIME_REQUIREMENTS, DEVELOPMENT_REQUIREMENTS):
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            match = REQUIREMENT_NAME.match(line)
            if match:
                found.add(match.group(1).casefold())
    return found


def test_every_declared_dependency_is_credited() -> None:
    credits_text = CREDITS.casefold()
    uncredited = sorted(
        name
        for name in declared()
        if SPELLED_DIFFERENTLY.get(name, name).casefold() not in credits_text
    )

    assert uncredited == []


def test_the_language_and_the_toolkit_are_credited_too() -> None:
    """Neither is a line in a requirements file; both are shipped."""
    for name in ("Python", "PySide6"):
        assert name.casefold() in CREDITS.casefold()
