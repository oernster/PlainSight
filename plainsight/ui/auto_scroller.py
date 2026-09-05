"""Content that reads itself: descend, hold, rewind fast, repeat.

A reader who takes over by hand suspends the cycle rather than switching it off;
it picks up from wherever they left it. A surface beneath a modal is frozen
in place rather than suspended, so it resumes exactly where it was.
"""

from __future__ import annotations

from enum import Enum, auto

from PySide6.QtCore import QEvent, QObject, QTimer
from PySide6.QtWidgets import QAbstractScrollArea, QApplication

TICK_MS = 40
START_HOLD_MS = 5000
BOTTOM_HOLD_MS = 5000
TOP_HOLD_MS = 2000
MANUAL_HOLD_MS = 2500
DESCENT_PIXELS = 1
DESCENT_TICKS_PER_STEP = 2
REWIND_PIXELS = 15
NO_OVERFLOW = 0

_WATCHED_EVENTS = (
    QEvent.Type.Wheel,
    QEvent.Type.MouseButtonPress,
    QEvent.Type.KeyPress,
    QEvent.Type.FocusIn,
)


class Phase(Enum):
    """Where in the cycle the surface currently is."""

    DOWN = auto()
    PAUSE_BOTTOM = auto()
    UP = auto()
    PAUSE_TOP = auto()
    MANUAL = auto()


class AutoScroller(QObject):
    """Drives one scrollable surface through the reading cycle."""

    def __init__(self, area: QAbstractScrollArea) -> None:
        super().__init__(area)
        self._area = area
        self._bar = area.verticalScrollBar()
        self._phase = Phase.PAUSE_TOP
        self._wait_ms = START_HOLD_MS
        self._steps_left = DESCENT_TICKS_PER_STEP
        self._start_hold_spent = False
        self._last_position = self._bar.value()
        self._timer = QTimer(self)
        self._timer.setInterval(TICK_MS)
        self._timer.timeout.connect(self.tick)
        self._timer.start()
        self._watch()

    def restart(self) -> None:
        """Return to the start hold, as a fresh surface would."""
        self._phase = Phase.PAUSE_TOP
        self._wait_ms = START_HOLD_MS
        self._steps_left = DESCENT_TICKS_PER_STEP
        self._start_hold_spent = False
        self._bar.setValue(NO_OVERFLOW)
        self._last_position = self._bar.value()

    @property
    def phase(self) -> Phase:
        """The phase the surface is in, for tests to read."""
        return self._phase

    def suspend(self) -> None:
        """A reader took over; hold still, then resume from here.

        Gated on the surface being active, so a modal's own reset of a frozen
        surface beneath it cannot be mistaken for a hand.
        """
        if not self._is_active():
            self._last_position = self._bar.value()
            return
        if not self._start_hold_spent:
            return
        self._phase = Phase.MANUAL
        self._wait_ms = MANUAL_HOLD_MS
        self._last_position = self._bar.value()

    def tick(self) -> None:
        """One step of the cycle."""
        if not self._is_active() or self._bar.maximum() == NO_OVERFLOW:
            return
        if self._wait_ms > 0:
            self._count_down()
            return
        if self._phase is Phase.DOWN:
            self._descend()
        elif self._phase is Phase.UP:
            self._rewind()

    def _count_down(self) -> None:
        """Spend one tick of the current hold, then choose what follows."""
        self._wait_ms -= TICK_MS
        if self._wait_ms > 0:
            return
        if self._phase is Phase.PAUSE_TOP:
            self._start_hold_spent = True
            self._phase = Phase.DOWN
        elif self._phase is Phase.PAUSE_BOTTOM:
            self._phase = Phase.UP
        else:
            self._phase = Phase.UP if self._at_bottom() else Phase.DOWN

    def _descend(self) -> None:
        """Advance one pixel every second tick, which is the reading pace."""
        self._steps_left -= 1
        if self._steps_left > 0:
            return
        self._steps_left = DESCENT_TICKS_PER_STEP
        self._move(self._bar.value() + DESCENT_PIXELS)
        if self._at_bottom():
            self._phase = Phase.PAUSE_BOTTOM
            self._wait_ms = BOTTOM_HOLD_MS

    def _rewind(self) -> None:
        """Travel back fast: a reposition rather than a reading pass."""
        self._move(max(NO_OVERFLOW, self._bar.value() - REWIND_PIXELS))
        if self._bar.value() <= NO_OVERFLOW:
            self._phase = Phase.PAUSE_TOP
            self._wait_ms = TOP_HOLD_MS

    def _move(self, position: int) -> None:
        """Place the bar, recording where the scroller itself put it."""
        self._bar.setValue(position)
        self._last_position = self._bar.value()

    def _at_bottom(self) -> bool:
        return self._bar.value() >= self._bar.maximum()

    def _is_active(self) -> bool:
        """False while a modal above this surface owns the screen."""
        modal = QApplication.activeModalWidget()
        if modal is None:
            return True
        window = self._area.window()
        return modal is window or modal.isAncestorOf(window)

    def _watch(self) -> None:
        """Every way a reader can take hold of this surface.

        All of it is local to the surface. Listening to the application for
        focus instead reached back to a surface that could already be gone,
        which took the whole process down on teardown; the surface's own focus
        event says the same thing and cannot outlive it.
        """
        self._area.installEventFilter(self)
        self._area.viewport().installEventFilter(self)
        self._bar.sliderPressed.connect(self.suspend)
        self._bar.sliderReleased.connect(self.suspend)
        self._bar.sliderMoved.connect(lambda _: self.suspend())

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        """Wheel, click and key on the surface all count as reading by hand."""
        if event.type() in _WATCHED_EVENTS:
            self.suspend()
        return super().eventFilter(watched, event)
