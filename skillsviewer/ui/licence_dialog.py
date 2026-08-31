"""One licence, shown at the width of its own text and reading itself down.

Licence texts arrive hard wrapped, so the dialog is sized to the document rather
than to a guessed minimum: wrapping them again would break lines twice.
"""

from __future__ import annotations

import math
from pathlib import Path

from PySide6.QtWidgets import QTextBrowser, QVBoxLayout, QWidget

from .auto_scroller import AutoScroller
from .widgets import FirstStopDialog, close_row

DIALOG_HEIGHT_PX = 520
WIDTH_CAP_PX = 900
MISSING_LICENCE = (
    "This licence text is not bundled with the application. "
    "See the project repository for it."
)


class LicenceDialog(FirstStopDialog):
    """A licence text, read only, with the reading cycle attached."""

    def __init__(self, title: str, path: Path | None, parent: QWidget | None) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.text = QTextBrowser(self)
        self.text.setObjectName("SkillView")
        self.text.setLineWrapMode(QTextBrowser.LineWrapMode.NoWrap)
        self.text.setPlainText(_read(path))
        self.scroller = AutoScroller(self.text)

        layout = QVBoxLayout(self)
        layout.addWidget(self.text)
        layout.addLayout(close_row(self))
        self.resize(self._fitted_width(), DIALOG_HEIGHT_PX)

    def _fitted_width(self) -> int:
        """The document's own width, plus the chrome around it, capped."""
        margins = self.layout().contentsMargins()
        chrome = (
            self.text.verticalScrollBar().sizeHint().width()
            + 2 * self.text.frameWidth()
            + margins.left()
            + margins.right()
        )
        wanted = math.ceil(self.text.document().idealWidth()) + chrome
        return min(wanted, WIDTH_CAP_PX)


def _read(path: Path | None) -> str:
    """The licence text; a note saying so when it is not bundled."""
    if path is None:
        return MISSING_LICENCE
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return MISSING_LICENCE
