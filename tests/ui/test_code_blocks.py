"""A preformatted block drawn as one box, with its line drawing intact.

Read off the laid-out document rather than the style sheet's text, since the
failure was in what Qt made of the markup: a background painted line by line,
the open prose spacing inherited from the cell and Courier New chosen unasked.
"""

from __future__ import annotations

from PySide6.QtGui import QTextDocument, QTextTable

from plainsight.domain.document import DocumentKind
from plainsight.infrastructure.renderer import DocumentHtmlRenderer
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


def test_plain_text_is_boxed_the_same_way(application) -> None:
    document = laid_out(DARK, DIAGRAM, DocumentKind.PLAIN_TEXT)

    box = the_box_around(document, "│ UI │")

    assert box.format().background().color().name() == DARK.code_background
