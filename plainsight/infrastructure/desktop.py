"""The two things handed to the desktop: an editor to start, a link to open.

Both are seams rather than direct calls from the window. Without them there is
no way to prove the right thing was asked for without either mocking Qt or
starting a real editor in the middle of a test run.
"""

from __future__ import annotations

from PySide6.QtCore import QProcess, QUrl
from PySide6.QtGui import QDesktopServices

from ..domain.settings import EditorChoice


class DesktopEditorLauncher:
    """Starts the chosen editor, detached from this process."""

    def launch(self, editor: EditorChoice, target: str) -> bool:
        """Open ``target`` in ``editor``; False when the desktop declined."""
        started, _pid = QProcess.startDetached(editor.path, [target])
        return bool(started)


class QtExternalOpener:
    """Hands an address to whatever the desktop opens links with."""

    def open(self, address: str) -> bool:
        """Ask for this address; False when the desktop declined."""
        return bool(QDesktopServices.openUrl(QUrl(address)))
