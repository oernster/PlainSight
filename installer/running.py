"""Finding and closing the application before any file is touched.

Extracting over a locked executable raises partway through and leaves a half
written install, so the question is asked first rather than recovered from.
"""

from __future__ import annotations

import subprocess
import sys

from installer import actions

NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
TASKLIST_TIMEOUT_S = 10
IS_WINDOWS = sys.platform == "win32"


def is_running() -> bool:
    """Whether the application is open right now."""
    if not IS_WINDOWS:
        return False
    completed = subprocess.run(
        ["tasklist", "/FI", f"IMAGENAME eq {actions.EXE_NAME}"],
        capture_output=True,
        text=True,
        creationflags=NO_WINDOW,
        timeout=TASKLIST_TIMEOUT_S,
        check=False,
    )
    return actions.EXE_NAME.lower() in completed.stdout.lower()


def close_it() -> bool:
    """Close the application by image name.

    By NAME and never by process tree: a tree kill decides descent from
    recorded parent process ids, which churn on a machine where the app has
    been started and killed repeatedly, so the setup program can end up
    recorded as a descendant and terminate itself.
    """
    if not IS_WINDOWS:
        return True
    completed = subprocess.run(
        ["taskkill", "/F", "/IM", actions.EXE_NAME],
        capture_output=True,
        creationflags=NO_WINDOW,
        timeout=TASKLIST_TIMEOUT_S,
        check=False,
    )
    return completed.returncode == 0
