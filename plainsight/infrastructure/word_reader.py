"""Reads a Word document by turning it into Markdown at the boundary.

Markdown rather than HTML, converted here rather than anywhere further in,
so that everything downstream stays exactly as it was: the softening, the
readable column and the renderer already handle a laid out document and have no
business knowing that this one arrived as a zip full of XML.

What is carried over is what a reader reads: headings, paragraphs, lists,
tables and the emphasis inside them. What is dropped is everything that is
presentation rather than content, since none of it survives the reading pane
anyway: fonts, colours, page furniture, positioned images and revision marks.
This is a reader, so a document it cannot represent perfectly is still better
shown than refused.
"""

from __future__ import annotations

from pathlib import Path

import docx
from docx.document import Document as WordDocument
from docx.oxml.ns import qn
from docx.table import Table
from docx.text.paragraph import Paragraph

from ..domain.document import DocumentBody, DocumentSummary

NOT_A_WORD_FILE = "This file could not be read as a Word document."
MISSING_WORD_FILE = "This file could not be opened."
EMPTY_WORD_FILE = "This Word document holds no text."

HEADING_PREFIX = "#"
MAX_HEADING_LEVEL = 6
BULLET = "-"
NUMBERED = "1."
TABLE_EDGE = "|"
LIST_STYLE_MARKER = "list"
NUMBER_STYLE_MARKER = "number"
HEADING_STYLE_MARKER = "heading"


class WordDocumentReader:
    """A Word document, read as the Markdown it is closest to."""

    def summarise(self, path: str) -> DocumentSummary:
        """Whether it opens at all. A Word document declares no frontmatter.

        Only the container is opened here, never the text pulled out of it.
        Extracting a document in order to list it would cost that extraction
        for every Word file beneath a folder in order to show one of them.
        """
        _, failure = _opened(path)
        return DocumentSummary(failure=failure)

    def read_body(self, path: str) -> DocumentBody:
        """The document as Markdown, else why there is none."""
        document, failure = _opened(path)
        if document is None:
            return DocumentBody(failure=failure)
        try:
            text = "\n\n".join(_blocks(document))
        except Exception:  # noqa: BLE001
            return DocumentBody(failure=NOT_A_WORD_FILE)
        if not text.strip():
            return DocumentBody(failure=EMPTY_WORD_FILE)
        return DocumentBody(text=text)


def _opened(path: str) -> tuple[WordDocument | None, str]:
    """The document with no failure; else nothing with a reason.

    Anything at all is caught, on purpose. This opens a file chosen by
    somebody else; a malformed one reaches an XML parser several layers
    down that has no contract with this application about what it raises.
    Measured: a zip holding a content type map that is merely the wrong shape
    comes back as an ``AttributeError`` from lxml; a list of the exception
    types seen so far is a list that a differently broken file gets to extend.
    A reader must not take the application down over a file that was clicked.

    Which failure it was is settled by looking for the file rather than by the
    exception, because python-docx raises the same ``PackageNotFoundError``
    for a file that is not there and one that is there but is not a Word
    document; those want different words in front of a reader.
    """
    try:
        return docx.Document(path), ""
    except OSError:
        return None, MISSING_WORD_FILE
    except Exception:  # noqa: BLE001
        return None, NOT_A_WORD_FILE if Path(path).is_file() else MISSING_WORD_FILE


def _blocks(document: WordDocument) -> list[str]:
    """Every paragraph and table, in the order they appear in the document.

    Walked over the body's own XML rather than over ``paragraphs`` and
    ``tables`` separately, because those are two lists in document order only
    within themselves: read that way a table lands after every paragraph in the
    file rather than between the two it sits between.
    """
    blocks: list[str] = []
    body = document.element.body
    for child in body.iterchildren():
        if child.tag == qn("w:p"):
            rendered = _paragraph(Paragraph(child, document))
            if rendered:
                blocks.append(rendered)
        elif child.tag == qn("w:tbl"):
            rendered = _table(Table(child, document))
            if rendered:
                blocks.append(rendered)
    return blocks


def _paragraph(paragraph: Paragraph) -> str:
    """One paragraph as Markdown; empty where it holds nothing to show."""
    text = _runs(paragraph)
    if not text.strip():
        return ""
    style = (paragraph.style.name or "").casefold()
    if HEADING_STYLE_MARKER in style:
        return f"{HEADING_PREFIX * _heading_level(style)} {text}"
    if NUMBER_STYLE_MARKER in style:
        return f"{NUMBERED} {text}"
    if LIST_STYLE_MARKER in style:
        return f"{BULLET} {text}"
    return text


def _heading_level(style: str) -> int:
    """The depth a heading style names; the shallowest when it names none.

    A style is called ``Heading 2`` in English and something else elsewhere,
    so the digit is taken where there is one rather than the name being
    matched. ``Title`` carries no digit and is the top of the document.
    """
    digits = "".join(character for character in style if character.isdigit())
    if not digits:
        return 1
    return min(int(digits), MAX_HEADING_LEVEL)


def _runs(paragraph: Paragraph) -> str:
    """The paragraph's text, keeping the emphasis Markdown can say."""
    pieces: list[str] = []
    for run in paragraph.runs:
        text = run.text
        if not text:
            continue
        if run.bold:
            text = f"**{text.strip()}**" if text.strip() else text
        if run.italic:
            text = f"*{text.strip()}*" if text.strip() else text
        pieces.append(text)
    return "".join(pieces)


def _table(table: Table) -> str:
    """A table as a Markdown table, its first row taken as the heading.

    Markdown has no table without a heading row, so the first row becomes one.
    That is what a Word table almost always opens with; where it does not, the
    first row of data reads as a heading, which is a good deal better than the
    table not appearing.
    """
    rows = [[" ".join(cell.text.split()) for cell in row.cells] for row in table.rows]
    if not rows:
        return ""
    width = max(len(row) for row in rows)
    lines = [_row(rows[0], width), _row([_RULE] * width, width)]
    lines.extend(_row(row, width) for row in rows[1:])
    return "\n".join(lines)


_RULE = "---"


def _row(cells: list[str], width: int) -> str:
    """One table row, padded to the width of the widest row in the table."""
    padded = list(cells) + [""] * (width - len(cells))
    return f"{TABLE_EDGE} " + f" {TABLE_EDGE} ".join(padded) + f" {TABLE_EDGE}"
