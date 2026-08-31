"""One explicit focus ring for the main window.

Tab and Right step forward, Shift+Tab and Left step back, both wrapping. The
horizontal arrows are tested first, so they step the ring everywhere and focus
is never trapped. Up and Down belong to whatever stop holds them.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence

from PySide6.QtCore import QEvent, QObject, Qt
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import QApplication, QPushButton, QWidget

FORWARD_KEYS = (Qt.Key.Key_Tab, Qt.Key.Key_Right)
BACK_KEYS = (Qt.Key.Key_Backtab, Qt.Key.Key_Left)
ACTIVATE_KEYS = (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space)
FIRST_STOP = 0
NOT_FOUND = -1


def is_live(widget: QWidget) -> bool:
    """Whether a stop can be reached: enabled, visible and takes tab focus."""
    return (
        widget.isEnabled()
        and widget.isVisible()
        and bool(widget.focusPolicy() & Qt.FocusPolicy.TabFocus)
    )


class KeyboardNavigator(QObject):
    """Drives the window's ring, recomputed live on every move."""

    def __init__(self, window: QWidget, stops: Callable[[], Sequence[QWidget]]) -> None:
        super().__init__(window)
        self._window = window
        self._stops = stops
        application = QApplication.instance()
        if application is not None:
            application.installEventFilter(self)

    def live_stops(self) -> list[QWidget]:
        """The ring as it stands now, dead stops passed over."""
        return [stop for stop in self._stops() if is_live(stop)]

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        """Step the ring; else hand the key back to the toolkit."""
        if event.type() is not QEvent.Type.KeyPress:
            return super().eventFilter(watched, event)
        if not self._window.isActiveWindow():
            return super().eventFilter(watched, event)
        if QApplication.activeModalWidget() is not None:
            return super().eventFilter(watched, event)
        # An open menu is a popup rather than a modal. While one is up the
        # focus widget is None, so the ring would read that as focus sitting
        # nowhere then jump to its first stop under the open menu. Measured, not
        # assumed: a popped QMenu is reported here and not by the modal check.
        if QApplication.activePopupWidget() is not None:
            return super().eventFilter(watched, event)
        return self._handle(event) or super().eventFilter(watched, event)

    def _handle(self, event: QEvent) -> bool:
        """True when this navigator consumed the key."""
        assert isinstance(event, QKeyEvent)
        key = event.key()
        if key in FORWARD_KEYS:
            return self._step(1)
        if key in BACK_KEYS:
            return self._step(-1)
        if key in ACTIVATE_KEYS:
            return self._activate()
        return False

    def _step(self, delta: int) -> bool:
        """Move to the next or previous stop, wrapping at both ends."""
        stops = self.live_stops()
        if not stops:
            return False
        index = self._current_index(stops)
        target = (
            stops[FIRST_STOP] if index == NOT_FOUND else self._next(stops, index, delta)
        )
        target.setFocus(Qt.FocusReason.TabFocusReason)
        return True

    def _next(self, stops: list[QWidget], index: int, delta: int) -> QWidget:
        return stops[(index + delta) % len(stops)]

    def _current_index(self, stops: list[QWidget]) -> int:
        """Where focus sits on the ring; NOT_FOUND when it sits nowhere."""
        focused = QApplication.focusWidget()
        if focused is None:
            return NOT_FOUND
        for position, stop in enumerate(stops):
            if stop is focused or stop.isAncestorOf(focused):
                return position
        return NOT_FOUND

    def _activate(self) -> bool:
        """Enter and Space press the focused button; Qt does not do this."""
        focused = QApplication.focusWidget()
        if isinstance(focused, QPushButton) and focused.isEnabled():
            focused.click()
            return True
        return False


class NeutralStart(QWidget):
    """A stop of no size that absorbs the window's first focus, once.

    The main window starts neutral: nothing is highlighted until the first Tab
    or Right press enters the ring. It leaves the tab chain the moment focus
    moves on, so the toolkit's own chain holds none of it either.
    """

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setFixedSize(0, 0)
        self.setFocusPolicy(Qt.FocusPolicy.TabFocus)

    def absorb(self) -> None:
        """Take the first focus, then leave the chain for good.

        The policy is dropped while the focus is still held, which Qt allows
        and which is why this is not done from a focus event: an event handler
        that touches the widget as the window is torn down crashes the process,
        measured rather than guessed.
        """
        self.setFocus(Qt.FocusReason.OtherFocusReason)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
