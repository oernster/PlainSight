"""Starting the application and bringing its window forward."""

from __future__ import annotations

import ctypes
import pathlib
import subprocess
import sys
from collections.abc import Callable

NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
WINDOWS = "win32"


def allow_foreground(process_id: int) -> bool:
    """Let the process just started take the foreground; False when it cannot.

    Windows refuses the foreground to a process that does not already hold it.
    Setup holds it at this moment, so it is the only thing that can hand the
    right over; without that the new window opens behind everything and does no
    more than flash on the taskbar. This is the granting half; the
    application asking for it in `present` is the other. Neither works alone.

    Anywhere but Windows there is no such rule and nothing to do.
    """
    if sys.platform != WINDOWS:
        return False
    try:
        user32 = ctypes.windll.user32  # type: ignore[attr-defined]
        return bool(user32.AllowSetForegroundWindow(process_id))
    except (AttributeError, OSError):
        return False


def start(
    executable: pathlib.Path,
    grant_foreground: Callable[[int], bool] = allow_foreground,
) -> bool:
    """Start the application detached; False when it would not start.

    Setup closes only after this returns: closing first hands the foreground
    back to whatever was behind it and the application then merely flashes on
    the taskbar. The grant is injected so a test can watch it happen without a
    real process being handed real foreground rights.
    """
    if not executable.is_file():
        return False
    try:
        process = subprocess.Popen(
            [str(executable)],
            cwd=str(executable.parent),
            creationflags=NO_WINDOW,
        )
    except OSError:
        return False
    grant_foreground(process.pid)
    return True
