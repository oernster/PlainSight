"""The reading cycle, driven by calling the tick rather than by waiting.

Every phase is a whole number of ticks, so counting calls is exact where waiting
five real seconds would be slow and flaky both.
"""

from __future__ import annotations

from PySide6.QtWidgets import QApplication, QTextBrowser

from skillsviewer.ui.auto_scroller import (
    BOTTOM_HOLD_MS,
    DESCENT_TICKS_PER_STEP,
    REWIND_PIXELS,
    START_HOLD_MS,
    TICK_MS,
    AutoScroller,
    Phase,
)

LONG_CONTENT = "<p>a line of text</p>" * 400
SHORT_CONTENT = "<p>one line</p>"
START_HOLD_TICKS = START_HOLD_MS // TICK_MS
BOTTOM_HOLD_TICKS = BOTTOM_HOLD_MS // TICK_MS


def a_surface(
    application: QApplication, html: str
) -> tuple[QTextBrowser, AutoScroller]:
    view = QTextBrowser()
    view.resize(300, 200)
    view.setHtml(html)
    view.show()
    QApplication.processEvents()
    scroller = AutoScroller(view)
    scroller._timer.stop()
    return view, scroller


def test_the_timer_is_running_before_a_test_stops_it(application) -> None:
    view = QTextBrowser()
    scroller = AutoScroller(view)

    assert scroller._timer.isActive()
    scroller._timer.stop()


def test_the_surface_holds_still_through_the_start_hold(application) -> None:
    view, scroller = a_surface(application, LONG_CONTENT)

    for _ in range(START_HOLD_TICKS - 1):
        scroller.tick()

    assert view.verticalScrollBar().value() == 0
    assert scroller.phase is Phase.PAUSE_TOP


def test_the_descent_begins_once_the_start_hold_is_spent(application) -> None:
    view, scroller = a_surface(application, LONG_CONTENT)

    for _ in range(START_HOLD_TICKS + DESCENT_TICKS_PER_STEP):
        scroller.tick()

    assert scroller.phase is Phase.DOWN
    assert view.verticalScrollBar().value() > 0


def test_the_descent_advances_one_pixel_every_second_tick(application) -> None:
    view, scroller = a_surface(application, LONG_CONTENT)
    for _ in range(START_HOLD_TICKS):
        scroller.tick()

    ticks = 20
    for _ in range(ticks):
        scroller.tick()

    assert view.verticalScrollBar().value() == ticks // DESCENT_TICKS_PER_STEP


def test_reaching_the_bottom_holds_then_rewinds(application) -> None:
    view, scroller = a_surface(application, LONG_CONTENT)
    bar = view.verticalScrollBar()
    for _ in range(START_HOLD_TICKS):
        scroller.tick()
    bar.setValue(bar.maximum() - 1)
    scroller._last_position = bar.value()

    for _ in range(DESCENT_TICKS_PER_STEP):
        scroller.tick()
    assert scroller.phase is Phase.PAUSE_BOTTOM

    for _ in range(BOTTOM_HOLD_TICKS + 1):
        scroller.tick()
    assert scroller.phase is Phase.UP


def test_the_rewind_returns_to_the_top_and_holds(application) -> None:
    view, scroller = a_surface(application, LONG_CONTENT)
    bar = view.verticalScrollBar()
    scroller._start_hold_spent = True
    scroller._phase = Phase.UP
    scroller._wait_ms = 0
    bar.setValue(bar.maximum())

    for _ in range((bar.maximum() // REWIND_PIXELS) + 1):
        scroller.tick()

    assert bar.value() == 0
    assert scroller.phase is Phase.PAUSE_TOP


def test_a_surface_that_does_not_overflow_never_moves(application) -> None:
    view, scroller = a_surface(application, SHORT_CONTENT)

    for _ in range(START_HOLD_TICKS * 2):
        scroller.tick()

    assert view.verticalScrollBar().value() == 0
    assert scroller.phase is Phase.PAUSE_TOP


def test_a_reader_taking_over_suspends_rather_than_stopping(application) -> None:
    _view, scroller = a_surface(application, LONG_CONTENT)
    for _ in range(START_HOLD_TICKS + 1):
        scroller.tick()

    scroller.suspend()

    assert scroller.phase is Phase.MANUAL


def test_the_cycle_resumes_from_where_the_reader_left_it(application) -> None:
    view, scroller = a_surface(application, LONG_CONTENT)
    for _ in range(START_HOLD_TICKS + 40):
        scroller.tick()
    left_at = view.verticalScrollBar().value()

    scroller.suspend()
    for _ in range((2500 // TICK_MS) + 1):
        scroller.tick()

    assert scroller.phase is Phase.DOWN
    assert view.verticalScrollBar().value() == left_at


def test_the_opening_focus_of_a_dialog_is_not_a_reader(application) -> None:
    _view, scroller = a_surface(application, LONG_CONTENT)

    scroller.suspend()

    assert scroller.phase is Phase.PAUSE_TOP
    assert scroller._wait_ms == START_HOLD_MS


def test_restarting_returns_the_surface_to_its_start_hold(application) -> None:
    view, scroller = a_surface(application, LONG_CONTENT)
    for _ in range(START_HOLD_TICKS + 40):
        scroller.tick()

    scroller.restart()

    assert scroller.phase is Phase.PAUSE_TOP
    assert scroller._wait_ms == START_HOLD_MS
    assert view.verticalScrollBar().value() == 0
