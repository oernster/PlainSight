"""Where the skills live when the user has not said otherwise.

Every operating system resolves to the same place beneath the home directory,
so there is one rule rather than three. The home directory itself is injected,
which is what makes this testable without an operating system.
"""

from __future__ import annotations

import os

from ..domain.settings import EditorChoice
from .ports import PathProbe, PlatformPaths

CLAUDE_DIRECTORY = ".claude"
NOTEPAD_PLUS_NAME = "Notepad++"
NOTEPAD_PLUS_FILE = "notepad++.exe"
NOTEPAD_NAME = "Notepad"
NOTEPAD_FILE = "notepad.exe"
SKILLS_DIRECTORY = "skills"
PLUGINS_DIRECTORY = "plugins"


def default_skills_root(paths: PlatformPaths) -> str:
    """The default skills root for the user this process is running as."""
    return os.path.join(paths.home_directory(), CLAUDE_DIRECTORY, SKILLS_DIRECTORY)


def effective_skills_root(remembered_root: str, paths: PlatformPaths) -> str:
    """The root to read: what the user chose, else the default."""
    chosen = remembered_root.strip()
    return chosen if chosen else default_skills_root(paths)


def plugins_root_for(skills_root: str) -> str:
    """The plugins tree that sits beside a skills folder.

    Both live under the same ``.claude`` directory, so the plugins tree is
    found from the skills root rather than guessed at separately. Browse
    somewhere with no plugins beside it and there is simply nothing to read,
    which is what makes an unrelated folder show one list and no grouping.
    """
    return os.path.join(
        os.path.dirname(os.path.normpath(skills_root)), PLUGINS_DIRECTORY
    )


def default_editor(paths: PlatformPaths, probe: PathProbe) -> EditorChoice | None:
    """The editor to hand a skill to when the user has not chosen one.

    Notepad++ where it is installed, since anyone who has it prefers it to what
    the system ships; otherwise the one every Windows machine already has. A
    machine that names neither a programs directory nor a system one gets no
    default at all, which leaves the control disabled and honest rather than
    pointing at something that is not there.
    """
    for directory in paths.program_directories():
        found = os.path.join(directory, NOTEPAD_PLUS_NAME, NOTEPAD_PLUS_FILE)
        if probe.exists(found):
            return EditorChoice(path=found, display_name=NOTEPAD_PLUS_NAME)
    system = paths.system_directory()
    if not system:
        return None
    plain = os.path.join(system, NOTEPAD_FILE)
    return (
        EditorChoice(path=plain, display_name=NOTEPAD_NAME)
        if probe.exists(plain)
        else None
    )
