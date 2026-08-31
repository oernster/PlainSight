"""One licence, shown at the width of its own text and reading itself down.

Licence texts arrive hard wrapped, so the dialog is sized to that wrapping
rather than to a guessed minimum. It is sized to the line nearly every line is
rather than to the longest, since fitting the longest leaves a band of empty
space beside all the others; the handful that run past it wrap, which costs a
line here and there and is what keeps the text off a sideways scrollbar.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QFontMetrics, QGuiApplication
from PySide6.QtWidgets import QVBoxLayout, QWidget

from .reading_pane import ReadingPane
from .widgets import FirstStopDialog, close_row

DIALOG_HEIGHT_PX = 520
# The cap exists to stop one pathological line making a dialog wider than the
# desk it sits on, so it is taken from the screen rather than written down. A
# fixed 900 was the old value and it was narrower than either licence this
# application ships, which put a horizontal scrollbar under text that had been
# wrapped by its author already.
SCREEN_FRACTION = 0.9
# Sized to the line most of the text is, not to the longest line in it. Fitting
# the longest left a wide band of empty space beside every ordinary line, since
# a licence is hard wrapped to about seventy characters with a handful of
# stragglers. The few that run past this wrap, which is why the text wraps at
# all: it is the only way to have neither a sideways scrollbar nor a dialog
# mostly full of nothing.
TYPICAL_LINE_FRACTION = 0.95
MINIMUM_WIDTH_PX = 640
SLACK_PX = 2
MISSING_LICENCE = (
    "This licence text is not bundled with the application. "
    "See the project repository for it."
)


class LicenceDialog(FirstStopDialog):
    """A licence text, read only, with the reading cycle attached."""

    def __init__(self, title: str, path: Path | None, parent: QWidget | None) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.text = ReadingPane(self)
        self.text.setPlainText(_read(path))

        layout = QVBoxLayout(self)
        layout.addWidget(self.text)
        layout.addLayout(close_row(self))
        self.resize(self._fitted_width(), DIALOG_HEIGHT_PX)

    def _fitted_width(self) -> int:
        """The width the body of the text wants, plus the chrome, capped.

        Polished first. A fresh widget carries the fallback font and none of
        the stylesheet's padding until it is, so measuring before that reports
        a document narrower than the one that gets drawn.
        """
        self.ensurePolished()
        self.text.ensurePolished()
        margins = self.layout().contentsMargins()
        chrome = (
            self.text.verticalScrollBar().sizeHint().width()
            + 2 * self.text.frameWidth()
            + margins.left()
            + margins.right()
        )
        return min(self._typical_line() + chrome + SLACK_PX, _cap(self))

    def _typical_line(self) -> int:
        """How wide nearly every line is, ignoring the few that run past it."""
        metrics = QFontMetrics(self.text.document().defaultFont())
        widths = sorted(
            metrics.horizontalAdvance(line)
            for line in self.text.toPlainText().splitlines()
        )
        if not widths:
            return MINIMUM_WIDTH_PX
        return widths[min(len(widths) - 1, int(len(widths) * TYPICAL_LINE_FRACTION))]


def _cap(dialog: QWidget) -> int:
    """As wide as the screen will take, never wider."""
    screen = dialog.screen() or QGuiApplication.primaryScreen()
    available = screen.availableGeometry().width() if screen is not None else 0
    return max(MINIMUM_WIDTH_PX, int(available * SCREEN_FRACTION))


def _read(path: Path | None) -> str:
    """The licence text; a note saying so when it is not bundled."""
    if path is None:
        return MISSING_LICENCE
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return MISSING_LICENCE
