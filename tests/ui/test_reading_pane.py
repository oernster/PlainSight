"""The shared reading region: how wide a line gets and how the text breathes.

What is asserted here is the mechanism rather than a character count. This
harness reports no font directory at all; its font metrics disagree with its
own text layout by nearly a factor of two, measured. So the number of
characters that ends up on a line is not a question it can answer. The rule
that produces that number is, so the rule is what gets pinned: a wider window
buys margins rather than a longer line; the column stops growing.
"""

from __future__ import annotations

from PySide6.QtWidgets import QApplication, QTextBrowser

from plainsight.ui import licence_dialog
from plainsight.ui.dialogs import find_licence
from plainsight.ui.reading_pane import MAX_LINE_CHARACTERS, ReadingPane
from plainsight.ui.theme import (
    DARK,
    LINE_HEIGHT_PERCENT,
    PARAGRAPH_GAP_PX,
    document_style,
    stylesheet,
)

WALL = "word " * 900
NARROW_PX = 400
WIDE_PX = 1400
WIDER_PX = 2000
TALL_PX = 700
NO_MARGIN = 0
NO_OVERFLOW = 0
A_REAL_LICENCE = find_licence("LICENSE-LGPL-3.0.txt")


def a_pane(application: QApplication, width: int, wrapped: bool = True) -> ReadingPane:
    pane = ReadingPane()
    if not wrapped:
        pane.setLineWrapMode(QTextBrowser.LineWrapMode.NoWrap)
    pane.document().setDefaultStyleSheet(document_style(DARK))
    pane.resize(width, TALL_PX)
    pane.show()
    QApplication.processEvents()
    # Content is set once the pane has its final width, as the application
    # does: a document laid out before the margins land reports a stale line.
    pane.setHtml(f"<p>{WALL}</p>")
    QApplication.processEvents()
    return pane


def test_a_wide_window_gives_margins_rather_than_longer_lines(application) -> None:
    wide = a_pane(application, WIDE_PX)
    wider = a_pane(application, WIDER_PX)

    grew_by = wider.viewport().width() - wide.viewport().width()

    assert wider.viewportMargins().left() > wide.viewportMargins().left()
    assert grew_by < WIDER_PX - WIDE_PX


def test_the_column_stops_at_the_width_the_pane_holds_it_to(application) -> None:
    pane = a_pane(application, WIDER_PX)

    assert pane.viewport().width() <= pane.readable_width()
    assert pane.viewport().width() < WIDER_PX


def test_a_narrow_window_keeps_every_pixel_it_has(application) -> None:
    pane = a_pane(application, NARROW_PX)

    assert pane.viewportMargins().left() == NO_MARGIN


def test_text_that_arrived_hard_wrapped_is_left_alone(application) -> None:
    """A licence is already wrapped; wrapping it again would break it twice."""
    pane = a_pane(application, WIDER_PX, wrapped=False)

    assert pane.viewportMargins().left() == NO_MARGIN


def test_the_readable_width_follows_the_length_it_holds_to(application) -> None:
    pane = a_pane(application, WIDE_PX)

    assert pane.readable_width() > MAX_LINE_CHARACTERS


def test_the_document_style_gives_the_text_room_to_breathe() -> None:
    style = document_style(DARK)

    assert f"line-height: {LINE_HEIGHT_PERCENT}%" in style
    assert f"margin-bottom: {PARAGRAPH_GAP_PX}px" in style


def test_open_spacing_makes_a_wall_of_text_taller_than_bare_colours(
    application,
) -> None:
    """The one reading of whether the spacing lands at all."""
    pane = a_pane(application, WIDE_PX)
    with_typography = pane.document().size().height()

    pane.document().setDefaultStyleSheet(f"body {{ color: {DARK.text}; }}")
    pane.setHtml(f"<p>{WALL}</p>")
    QApplication.processEvents()

    assert with_typography > pane.document().size().height()


def test_text_is_shown_in_full_when_the_screen_can_take_it(
    application, tmp_path
) -> None:
    """No horizontal scrollbar under text its author already wrapped.

    The cap was a flat 900 pixels, narrower than either licence this project
    ships, so both opened with a horizontal scrollbar under hard wrapped text.
    It follows the screen now, which is the only width a dialog genuinely
    cannot exceed. The document here is narrow enough that the cap cannot bind,
    so what is measured is the fitting rather than the cap.
    """
    # The stylesheet is set here rather than left to whichever test ran last:
    # it carries the padding and the font size the measurement has to account
    # for; the dialog is never used in the application without it.
    QApplication.instance().setStyleSheet(stylesheet(DARK))
    narrow = tmp_path / "LICENCE.txt"
    narrow.write_text("A short licence line.\n" * 40, encoding="utf-8")

    dialog = licence_dialog.LicenceDialog("A licence", narrow, None)
    dialog.show()
    QApplication.processEvents()

    assert dialog.text.horizontalScrollBar().maximum() == NO_OVERFLOW


def test_a_document_wider_than_the_screen_is_held_to_the_cap(
    application, tmp_path
) -> None:
    wide = tmp_path / "LICENCE.txt"
    wide.write_text("word " * 400, encoding="utf-8")

    dialog = licence_dialog.LicenceDialog("A licence", wide, None)
    dialog.show()
    QApplication.processEvents()

    assert dialog.width() == licence_dialog._cap(dialog)


def test_the_width_never_runs_past_what_the_screen_can_show(application) -> None:
    dialog = licence_dialog.LicenceDialog("A licence", A_REAL_LICENCE, None)
    dialog.show()
    QApplication.processEvents()

    assert dialog.width() <= licence_dialog._cap(dialog)


def test_the_cap_is_taken_from_the_screen_rather_than_written_down(
    application,
) -> None:
    dialog = licence_dialog.LicenceDialog("A licence", None, None)
    screen = dialog.screen()

    expected = int(screen.availableGeometry().width() * licence_dialog.SCREEN_FRACTION)

    assert licence_dialog._cap(dialog) == max(licence_dialog.MINIMUM_WIDTH_PX, expected)
