"""A preformatted block drawn as one box, with its line drawing intact.

Read off the laid-out document rather than the style sheet's text, since the
failure was in what Qt made of the markup: a background painted line by line,
the open prose spacing inherited from the cell and Courier New chosen unasked.
"""

from __future__ import annotations

from PySide6.QtGui import QTextDocument, QTextTable
from PySide6.QtWidgets import QApplication

from plainsight.domain.document import DocumentKind
from plainsight.infrastructure.renderer import DocumentHtmlRenderer
from plainsight.ui.reading_pane import MAX_LINE_CHARACTERS, ReadingPane
from plainsight.ui.theme import (
    CODE_LINE_HEIGHT_PERCENT,
    DARK,
    LIGHT,
    MONOSPACE_FAMILIES,
    document_style,
)

DIAGRAM = "┌────┐\n│ UI │\n└────┘"
FENCED = f"Before.\n\n```text\n{DIAGRAM}\n```\n\nAfter.\n"
FIRST_FAMILY = MONOSPACE_FAMILIES.split(",")[0].strip().strip('"')
# Wider than the column at any font this harness might pick, so what is
# measured is the rule rather than a character count.
WIDER_THAN_ANY_COLUMN = 6
WIDE_DIAGRAM = (
    "```text\n" + "─" * (MAX_LINE_CHARACTERS * WIDER_THAN_ANY_COLUMN) + "\n```\n"
)
NARROW_PX = 400
WIDE_PX = 2400
TALL_PX = 700
NOTHING_HIDDEN = 0
NO_MARGIN = 0


def laid_out(palette, body: str = FENCED, kind=DocumentKind.MARKDOWN):
    document = QTextDocument()
    document.setDefaultStyleSheet(document_style(palette))
    document.setHtml(DocumentHtmlRenderer().render(body, kind))
    return document


def the_box_around(document: QTextDocument, text: str) -> QTextTable:
    table = document.find(text).currentTable()
    assert table is not None, f"{text!r} is not inside a box"
    return table


def test_a_fenced_block_is_one_box_in_the_code_colour(application) -> None:
    for palette in (DARK, LIGHT):
        document = laid_out(palette)

        box = the_box_around(document, "│ UI │")

        assert box.format().background().color().name() == palette.code_background
        assert (box.rows(), box.columns()) == (1, 1)
        assert box.format().cellSpacing() == 0
        assert document.find("└────┘").currentTable() == box


def test_the_prose_around_a_block_is_not_boxed(application) -> None:
    document = laid_out(DARK)

    assert document.find("Before.").currentTable() is None
    assert document.find("After.").currentTable() is None


def test_a_box_holds_its_lines_at_their_own_height(application) -> None:
    """The cell's open prose spacing would cut every vertical stroke into dashes."""
    document = laid_out(DARK)

    block = document.find("│ UI │").block().blockFormat()

    assert block.lineHeight() == CODE_LINE_HEIGHT_PERCENT


def test_a_box_asks_for_a_face_with_whole_line_drawing(application) -> None:
    document = laid_out(DARK)

    families = document.find("│ UI │").charFormat().fontFamilies()

    assert families[0] == FIRST_FAMILY


def a_pane(width: int) -> ReadingPane:
    pane = ReadingPane()
    pane.document().setDefaultStyleSheet(document_style(DARK))
    pane.resize(width, TALL_PX)
    pane.show()
    QApplication.processEvents()
    pane.setHtml(DocumentHtmlRenderer().render(WIDE_DIAGRAM, DocumentKind.MARKDOWN))
    QApplication.processEvents()
    pane.apply_measure()
    QApplication.processEvents()
    return pane


def test_a_block_too_wide_to_wrap_takes_the_room_the_window_has(
    application,
) -> None:
    """The margins are for prose. A diagram was penned into the column.

    Read against the pane's own numbers rather than a character count, since
    this harness reports font metrics that disagree with its own layout.
    """
    pane = a_pane(WIDE_PX)
    margins = pane.viewportMargins()
    room = pane.viewport().width() + margins.left() + margins.right()

    assert pane.document().idealWidth() > pane.lineWrapColumnOrWidth()
    assert pane.viewport().width() > pane.lineWrapColumnOrWidth()
    assert pane.viewport().width() >= min(pane.document().idealWidth(), room)


def test_the_prose_column_is_capped_all_the_same(application) -> None:
    pane = a_pane(WIDE_PX)

    assert pane.lineWrapColumnOrWidth() == pane.readable_width()


def test_a_window_too_narrow_for_the_block_keeps_every_pixel(application) -> None:
    pane = a_pane(NARROW_PX)

    assert pane.viewportMargins().left() == NO_MARGIN
    assert pane.horizontalScrollBar().maximum() > NOTHING_HIDDEN


def test_plain_text_is_boxed_the_same_way(application) -> None:
    document = laid_out(DARK, DIAGRAM, DocumentKind.PLAIN_TEXT)

    box = the_box_around(document, "│ UI │")

    assert box.format().background().color().name() == DARK.code_background
