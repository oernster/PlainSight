"""A plain record of what the setup program did, in order.

The worst installer failures are the ones that never raise, so every step is
written down and flushed as it happens rather than at the end.
"""

from __future__ import annotations

import pathlib
import tempfile

LOG_NAME = "skillsviewer-setup.log"


class StepLog:
    """The record of what happened, flushed per step."""

    def __init__(self) -> None:
        self.path = pathlib.Path(tempfile.gettempdir()) / LOG_NAME
        self.lines: list[str] = []

    def write(self, message: str) -> None:
        """Record one step and flush it, so a crash still leaves the trail."""
        self.lines.append(message)
        try:
            self.path.write_text("\n".join(self.lines), encoding="utf-8")
        except OSError:
            pass
