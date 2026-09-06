"""Which folder is read; where the chooser opens when none has been.

**Nothing is read until the user chooses a folder.** A reader who has chosen
nothing gets an empty tree and an invitation, not a walk of their home
directory: reading a person's files is theirs to authorise, so on a machine
where permissions are explicit an unasked scan is a rummage through directories
nobody offered. The documents folder is where the chooser OPENS; it is not read
unless the user takes it.

The chooser opens somewhere ordinary on purpose. It used to open on the Claude
skills folder, which lives inside a dotted directory the operating system
treats as the application's own business rather than the user's; opening there
spent a permission the application has no business spending before the user has
asked for anything. The documents folder every desktop already gives its user
costs nothing to offer; the home directory stands in where a machine names no
such folder.

The same rule governs the plugins tree beside a chosen folder. It is read only
where the chosen folder is itself a Claude skills folder, which is to say a
``skills`` directory inside a ``.claude`` one. Anywhere else there is no sibling
the user implied, so none is looked at: choosing a notes folder must not send
this reading its neighbour.

Every operating system resolves to the same place beneath the home directory,
so there is one rule rather than three. The home directory itself is injected,
which is what makes this testable without an operating system.
"""

from __future__ import annotations

import os

from ..domain.settings import EditorChoice
from .ports import PathProbe, PlatformPaths

CLAUDE_DIRECTORY = ".claude"
DOCUMENTS_DIRECTORY = "Documents"
NOTEPAD_PLUS_NAME = "Notepad++"
NOTEPAD_PLUS_FILE = "notepad++.exe"
NOTEPAD_NAME = "Notepad"
NOTEPAD_FILE = "notepad.exe"
SKILLS_DIRECTORY = "skills"
PLUGINS_DIRECTORY = "plugins"


def documents_root(paths: PlatformPaths, probe: PathProbe) -> str:
    """The user's own documents folder; their home directory where there is none.

    Somewhere the chooser opens, never somewhere read on its own account. The
    folder is probed rather than assumed because a machine can be set up
    without one; a chooser pointed at a folder that is not there opens
    somewhere arbitrary instead of where it was sent.
    """
    home = paths.home_directory()
    documents = os.path.join(home, DOCUMENTS_DIRECTORY)
    return documents if probe.exists(documents) else home


def chosen_root(remembered_root: str) -> str:
    """The folder to read: what the user chose, else nothing at all.

    There is deliberately no fallback. A blank answer here is what makes the
    application read nothing until it is pointed somewhere.
    """
    return remembered_root.strip()


def browse_from(remembered_root: str, paths: PlatformPaths, probe: PathProbe) -> str:
    """Where the folder chooser opens: the last choice, else the documents folder.

    This is a starting place for a dialog the user is standing in front of, so
    it reads nothing itself. Somewhere the user already keeps their own files
    is the ordinary place to start; it asks the operating system for nothing
    the user has not already granted.
    """
    return chosen_root(remembered_root) or documents_root(paths, probe)


def plugins_root_for(root: str) -> str:
    """The plugins tree the chosen folder implies; empty when it implies none.

    A Claude skills folder has a plugins tree for a sibling under the same
    ``.claude`` directory; a reader who points at one plainly means that
    pair. Any other folder implies nothing about its neighbours, so nothing is
    looked at beside it: pointing this at a notes folder must not send it
    reading whatever happens to sit next door.
    """
    normalised = os.path.normpath(root)
    parent = os.path.dirname(normalised)
    if os.path.basename(normalised) != SKILLS_DIRECTORY:
        return ""
    if os.path.basename(parent) != CLAUDE_DIRECTORY:
        return ""
    return os.path.join(parent, PLUGINS_DIRECTORY)


def default_editor(paths: PlatformPaths, probe: PathProbe) -> EditorChoice | None:
    """The editor to hand a document to when the user has not chosen one.

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
