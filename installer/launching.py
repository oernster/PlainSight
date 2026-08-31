"""Starting the application and bringing its window forward."""

from __future__ import annotations

import pathlib
import subprocess

NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def start(executable: pathlib.Path) -> bool:
    """Start the application detached; False when it would not start.

    Setup closes only after this returns: closing first hands the foreground
    back to whatever was behind it and the application then merely flashes on
    the taskbar.
    """
    if not executable.is_file():
        return False
    try:
        subprocess.Popen(
            [str(executable)],
            cwd=str(executable.parent),
            creationflags=NO_WINDOW,
        )
    except OSError:
        return False
    return True
