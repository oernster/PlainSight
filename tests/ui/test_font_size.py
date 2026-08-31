"""The text size control: one button stepping a cycle of three."""

from __future__ import annotations

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QLabel, QPushButton, QWidget

from skillsviewer.domain.settings import DEFAULT_FONT_SIZE, FontSize
from skillsviewer.ui import top_tray
from skillsviewer.ui.main_window import MainWindow
from skillsviewer.ui.theme import DARK, FONT_SIZE_PX, stylesheet

# Wide enough that the tray lays out as it really does, rather than
# compressed into an order the measurement cannot read.
WIDE_PX = 1100
TALL_PX = 760


def a_measured_size(size: FontSize) -> int:
    """What a plain label actually ends up drawn at under this size.

    Read off the widget's own font after the stylesheet is applied rather than
    off the template, so the assertion is that the rule reaches a widget rather
    than that a string was formatted.
    """
    QApplication.instance().setStyleSheet(stylesheet(DARK, size))
    label = QLabel("measured")
    label.ensurePolished()
    return label.font().pixelSize()


def test_the_button_sits_right_of_the_editor_control(window: MainWindow) -> None:
    stops = window.top_tray.ring_stops()

    assert stops[stops.index(window.top_tray.font_size_button) - 1] is (
        window.top_tray.open_in_editor_button
    )


def test_a_separator_stands_between_those_two(window: MainWindow) -> None:
    tray = window.top_tray
    window.resize(WIDE_PX, TALL_PX)
    QApplication.processEvents()

    def centre(widget: QWidget) -> int:
        return widget.mapTo(window, widget.rect().center()).x()

    assert centre(tray.open_in_editor_button) < centre(tray.separator)
    assert centre(tray.separator) < centre(tray.font_size_button)


def test_the_separator_is_no_focus_stop(window: MainWindow) -> None:
    """A container never takes focus and never appears in the ring."""
    assert window.top_tray.separator.focusPolicy() is Qt.FocusPolicy.NoFocus
    assert window.top_tray.separator not in window.ring_stops()
    assert not isinstance(window.top_tray.separator, QPushButton)


def test_the_button_opens_wearing_the_size_it_would_move_to(
    window: MainWindow,
) -> None:
    moving_to = DEFAULT_FONT_SIZE.next_in_cycle

    assert window.top_tray.font_size_button.toolTip() == (
        top_tray.FONT_SIZE_TOOLTIPS[moving_to]
    )


def test_pressing_it_walks_the_whole_cycle_and_returns(window: MainWindow) -> None:
    seen = []
    for _press in FontSize:
        seen.append(window._font_size)
        window.top_tray.font_size_button.click()

    assert seen == [FontSize.MEDIUM, FontSize.LARGE, FontSize.EXTRA_LARGE]
    assert window._font_size is FontSize.MEDIUM


def test_the_button_always_shows_the_next_size_rather_than_the_current_one(
    window: MainWindow,
) -> None:
    for _press in FontSize:
        expected = window._font_size.next_in_cycle
        assert window.top_tray.font_size_button.toolTip() == (
            top_tray.FONT_SIZE_TOOLTIPS[expected]
        )
        window.top_tray.font_size_button.click()


def test_every_size_has_its_own_artwork_and_it_is_really_there(
    window: MainWindow,
) -> None:
    found = {
        size: window._assets.find(name)
        for size, name in top_tray.FONT_SIZE_ICONS.items()
    }

    assert set(top_tray.FONT_SIZE_ICONS) == set(FontSize)
    assert [path for path in found.values() if path is None] == []
    assert not window.top_tray.font_size_button.icon().isNull()


@pytest.mark.parametrize("size", list(FontSize))
def test_each_size_reaches_a_real_widget(size: FontSize) -> None:
    assert a_measured_size(size) == FONT_SIZE_PX[size]


def test_the_sizes_genuinely_differ_and_grow() -> None:
    measured = [a_measured_size(size) for size in FontSize]

    assert measured == sorted(measured)
    assert len(set(measured)) == len(measured)


def test_a_remembered_size_is_worn_on_the_next_run(window: MainWindow) -> None:
    window.top_tray.font_size_button.click()
    assert window._service.font_size() is FontSize.LARGE

    again = MainWindow(window._service, window._renderer, window._assets)

    assert again._font_size is FontSize.LARGE
    assert again.top_tray.font_size_button.toolTip() == (
        top_tray.FONT_SIZE_TOOLTIPS[FontSize.EXTRA_LARGE]
    )
    again.deleteLater()


def test_changing_the_size_leaves_the_appearance_alone(window: MainWindow) -> None:
    before = window._appearance()

    window.top_tray.font_size_button.click()

    assert window._appearance() is before
