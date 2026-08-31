"""The few questions the application asks about the machine it runs on.

The locations are reported; which program to look for in them is the
application's business, not this module's.
"""

from __future__ import annotations

import os
from pathlib import Path

APPLICATION_DIRECTORY = "SkillsViewer"
SETTINGS_FILE_NAME = "settings.json"
PROGRAM_VARIABLES = ("ProgramFiles", "ProgramFiles(x86)", "ProgramW6432")
SYSTEM_VARIABLE = "SystemRoot"
SYSTEM_PROGRAMS = "System32"


class HomePlatformPaths:
    """Locations derived from the home directory of the current user."""

    def home_directory(self) -> str:
        """The current user's home directory."""
        return str(Path.home())

    def program_directories(self) -> tuple[str, ...]:
        """Every programs directory this machine names, in the order named.

        Read from the environment rather than written down, since the drive and
        even the folder name differ between machines and between languages. An
        operating system that names none reports none, which is the whole
        answer rather than a failure.
        """
        found = (os.environ.get(name, "") for name in PROGRAM_VARIABLES)
        return tuple(dict.fromkeys(place for place in found if place))

    def system_directory(self) -> str:
        """Where the operating system keeps its own programs; empty if none."""
        root = os.environ.get(SYSTEM_VARIABLE, "")
        return os.path.join(root, SYSTEM_PROGRAMS) if root else ""


class FileSystemPathProbe:
    """Answers whether a path is there, without reading it."""

    def exists(self, path: str) -> bool:
        """Whether something exists at this path."""
        return Path(path).exists()


def settings_path() -> Path:
    """Where the settings file lives for the current user."""
    return Path.home() / f".{APPLICATION_DIRECTORY.lower()}" / SETTINGS_FILE_NAME
