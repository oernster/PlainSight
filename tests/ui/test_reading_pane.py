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

from skillsviewer.ui.reading_pane import MAX_LINE_CHARACTERS, ReadingPane
from skillsviewer.ui.theme import (
    DARK,
    LINE_HEIGHT_PERCENT,
    PARAGRAPH_GAP_PX,
    document_style,
)

WALL = "word " * 900
NARROW_PX = 400
WIDE_PX = 1400
WIDER_PX = 2000
TALL_PX = 700
NO_MARGIN = 0


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
