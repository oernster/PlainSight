"""One home for how a scrolling text region behaves.

Three surfaces read a long document: the document pane, the About dialog and a
licence. They had drifted apart, each attaching the reading cycle by hand and
none but the document pane gating its own focus. A region that scrolls is a stop
while it overflows and none while it fits; Home and End reach its ends. Saying
that once here is what stops the three answering differently.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QFontMetrics, QKeyEvent
from PySide6.QtWidgets import QTextBrowser, QWidget

from .auto_scroller import AutoScroller

PANE_NAME = "ReadingPane"
NO_OVERFLOW = 0
TOP = 0
TOP_KEYS = (Qt.Key.Key_Home,)
BOTTOM_KEYS = (Qt.Key.Key_End,)
MAX_LINE_CHARACTERS = 90
NO_MARGIN = 0
SIDES = 2
ALPHABET = "abcdefghijklmnopqrstuvwxyz"


class ReadingPane(QTextBrowser):
    """A read-only document that reads itself and answers the ends keys."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName(PANE_NAME)
        self.setReadOnly(True)
        self._scroller = AutoScroller(self)
        self.sync_focus_policy()

    @property
    def scroller(self) -> AutoScroller:
        """The reading cycle, for tests and for a caller to restart."""
        return self._scroller

    def sync_focus_policy(self) -> None:
        """A stop while it overflows; never otherwise.

        A page that fits scrolls nowhere, so focusing it would let the reader
        do nothing. Recomputed on every resize and every fresh document.

        Reachable by a click as well as by Tab. Tab alone was measured to be
        the whole of it, which meant clicking the text you were reading did
        not focus it, so the keys that move around a document went to whatever
        held focus instead and looked broken.
        """
        overflows = self.verticalScrollBar().maximum() > NO_OVERFLOW
        self.setFocusPolicy(
            Qt.FocusPolicy.StrongFocus if overflows else Qt.FocusPolicy.NoFocus
        )

    def resizeEvent(self, event: object) -> None:
        super().resizeEvent(event)  # type: ignore[arg-type]
        self.apply_measure()
        self.sync_focus_policy()

    def apply_measure(self) -> None:
        """Hold the text column to a readable line length.

        A wide window turns a long paragraph into a wall: the eye loses the
        line it was on when it travels back for the next one. The column is
        capped instead of the window, so widening the window gives margins
        rather than longer lines. Text that arrived hard wrapped, a licence
        being the case, is left exactly as it came.
        """
        if self.lineWrapMode() is QTextBrowser.LineWrapMode.NoWrap:
            return
        slack = self.width() - self.readable_width()
        side = max(NO_MARGIN, slack // SIDES)
        self.setViewportMargins(side, NO_MARGIN, side, NO_MARGIN)

    def readable_width(self) -> int:
        """The width this pane's own font needs for a line of that length.

        Measured from a real string in the font actually in use rather than
        taken from ``averageCharWidth``, which reported twice the true figure
        here and would have widened the column instead of capping it.
        """
        advance = QFontMetrics(self.font()).horizontalAdvance(ALPHABET)
        return round(advance / len(ALPHABET) * MAX_LINE_CHARACTERS)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """Home goes to the top of the page and End to the foot of it.

        Measured, not assumed: Qt binds the bare keys on a read-only browser
        already but leaves Ctrl+Home and Ctrl+End unhandled, which is the pair
        a reader reaches for first. Both chords are answered here so all four
        behave alike rather than two of them silently doing nothing. The
        reading cycle watches this same press and suspends, so the jump lands
        and holds rather than being carried straight back down.
        """
        bar = self.verticalScrollBar()
        if event.key() in TOP_KEYS:
            bar.setValue(TOP)
            event.accept()
            return
        if event.key() in BOTTOM_KEYS:
            bar.setValue(bar.maximum())
            event.accept()
            return
        super().keyPressEvent(event)
