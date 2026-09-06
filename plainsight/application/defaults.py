"""Which folder is read; where the chooser opens when none has been.

**Nothing is read until the user chooses a folder.** A reader who has chosen
nothing gets an empty tree and an invitation, not a walk of their home
directory: reading a person's files is theirs to authorise, so on a machine
where permissions are explicit an unasked scan is a rummage through directories
nobody offered. The home directory is where the chooser OPENS; it is not read
unless the user takes it.

The home directory is chosen because it is the one place no operating system
gates. It used to be the Claude skills folder, which lives inside a dotted
directory belonging to another application: the wrong place to point a document
reader, whatever the permissions. The obvious alternative is the documents
folder; that is not it either, because macOS gates ``Documents`` by name
alongside ``Desktop`` and ``Downloads`` while leaving the home directory
itself alone. Opening on the home directory therefore asks for nothing on any
of the three, with the documents folder one row down the listing for anyone
who wants it.

The same rule governs the plugins tree beside a chosen folder. It is read only
where the chosen folder is itself a Claude skills folder, which is to say a
``skills`` directory inside a ``.claude`` one. Anywhere else there is no sibling
the user implied, so none is looked at: choosing a notes folder must not send
this reading its neighbour.

One rule serves all three operating systems, since every one of them gives a
user a home directory. That directory is injected, which is what makes this
testable without an operating system.
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


def home_root(paths: PlatformPaths) -> str:
    """The user's home directory: somewhere the chooser opens, never read.

    Nothing is joined onto it. Every folder that could be named here is one
    the operating system may gate, where the home directory itself is on every
    machine and gated on none of them.
    """
    return paths.home_directory()


def chosen_root(remembered_root: str) -> str:
    """The folder to read: what the user chose, else nothing at all.

    There is deliberately no fallback. A blank answer here is what makes the
    application read nothing until it is pointed somewhere.
    """
    return remembered_root.strip()


def browse_from(remembered_root: str, paths: PlatformPaths) -> str:
    """Where the folder chooser opens: the last choice, else the home directory.

    This is a starting place for a dialog the user is standing in front of, so
    it reads nothing itself. The home directory is the one starting place no
    operating system asks the user to approve.
    """
    return chosen_root(remembered_root) or home_root(paths)


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
