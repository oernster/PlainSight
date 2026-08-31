"""What is already on this machine, read once before anything is drawn.

The options then open on what is true rather than all ticked, so a user who
deliberately declined a desktop shortcut is not offered one again as though
they had asked for it.
"""

from __future__ import annotations

import pathlib
from dataclasses import dataclass

from installer import actions
from installer.registry import read_registered


@dataclass(frozen=True, slots=True)
class Existing:
    """What the machine already holds, at the moment setup started."""

    version: str
    location: pathlib.Path
    desktop: bool
    start_menu: bool

    @property
    def installed(self) -> bool:
        """Whether there is an install to talk about at all."""
        return bool(self.version)

    @property
    def executable(self) -> pathlib.Path:
        """The installed application, wherever the Apps list says it is."""
        return actions.executable_path(self.location)


def look() -> Existing:
    """Read the registry and the shortcut folders as they stand."""
    recorded = read_registered()
    location = pathlib.Path(
        recorded.get("InstallLocation", str(actions.default_target()))
    )
    desktop, start_menu = actions.shortcut_paths()
    return Existing(
        version=recorded.get("DisplayVersion", ""),
        location=location,
        desktop=desktop.exists(),
        start_menu=start_menu.exists(),
    )
