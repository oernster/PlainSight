"""The one licence the setup program carries: the Qt LGPL it is covered by.

An application's own split into a model licence and an interface licence
belongs to the application, not to the program that installs it.
"""

from __future__ import annotations

import pathlib

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QTextBrowser, QVBoxLayout, QWidget

WINDOW_WIDTH_PX = 700
WINDOW_HEIGHT_PX = 520
TITLE = "Setup licence"
MISSING = "The licence text is not bundled with this setup program."


class LicenceWindow(QWidget):
    """A plain reader for one licence text."""

    def __init__(self, path: pathlib.Path | None, parent: QWidget | None) -> None:
        super().__init__(parent, Qt.WindowType.Window)
        self.setWindowTitle(TITLE)
        self.resize(WINDOW_WIDTH_PX, WINDOW_HEIGHT_PX)
        text = QTextBrowser(self)
        text.setPlainText(_read(path))
        column = QVBoxLayout(self)
        column.addWidget(text)


def _read(path: pathlib.Path | None) -> str:
    """The licence text; a note saying so when it is not bundled."""
    if path is None:
        return MISSING
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return MISSING
