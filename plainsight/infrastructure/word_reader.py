"""Reads a Word document by turning it into HTML at the boundary.

HTML rather than Markdown, converted here rather than anywhere further in, so
that everything downstream stays as it was: the reading pane already shows a
document that arrived as HTML and has no business knowing that this one
started as a zip full of XML.

Markdown was the first answer and was the wrong one. It is a narrower language
than a Word document and an ambiguous one, so text that means nothing in Word
turns into syntax on the way through: a paragraph the author indented with
four spaces came back as a block of code, shown as a wall of monospace clipped
at the right edge. That is one instance of a class with no end to it, whereas
escaping into HTML is total; `word_html` holds the reasoning in full.

What is carried over is what a reader reads: headings, paragraphs, lists,
tables and the emphasis inside them. What is dropped is everything that is
presentation rather than content, since none of it survives the reading pane
anyway: fonts, colours, page furniture, positioned images and revision marks.
This is a reader, so a document it cannot represent perfectly is still better
shown than refused.
"""

from __future__ import annotations

from itertools import groupby
from pathlib import Path

import docx
from docx.document import Document as WordDocument
from docx.oxml.ns import qn
from docx.table import Table
from docx.text.paragraph import Paragraph
from docx.text.run import Run

from ..domain.document import DocumentBody, DocumentSummary
from .word_html import (
    BULLETED,
    NO_HEADING,
    NUMBERED,
    Block,
    Piece,
    assembled,
    paragraph,
    plain,
    table,
)

NOT_A_WORD_FILE = "This file could not be read as a Word document."
MISSING_WORD_FILE = "This file could not be opened."
EMPTY_WORD_FILE = "This Word document holds no text."

# A table earns a table by having something to tabulate: rows AND columns.
LEAST_TABULAR = 2
SHALLOWEST_HEADING = 1
LIST_STYLE_MARKER = "list"
NUMBER_STYLE_MARKER = "number"
HEADING_STYLE_MARKER = "heading"


class WordDocumentReader:
    """A Word document, read as the HTML a reading surface can show."""

    def summarise(self, path: str) -> DocumentSummary:
        """Whether it opens at all. A Word document declares no frontmatter.

        Only the container is opened here, never the text pulled out of it.
        Extracting a document in order to list it would cost that extraction
        for every Word file beneath a folder in order to show one of them.
        """
        _, failure = _opened(path)
        return DocumentSummary(failure=failure)

    def read_body(self, path: str) -> DocumentBody:
        """The document as HTML, else why there is none."""
        document, failure = _opened(path)
        if document is None:
            return DocumentBody(failure=failure)
        try:
            text = assembled(_blocks(document))
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


def _blocks(document: WordDocument) -> list[Block]:
    """Every paragraph and table, in the order they appear in the document.

    Walked over the body's own XML rather than over ``paragraphs`` and
    ``tables`` separately, because those are two lists in document order only
    within themselves: read that way a table lands after every paragraph in the
    file rather than between the two it sits between.
    """
    blocks: list[Block] = []
    body = document.element.body
    for child in body.iterchildren():
        if child.tag == qn("w:p"):
            blocks.extend(_paragraph(Paragraph(child, document)))
        elif child.tag == qn("w:tbl"):
            blocks.extend(_table(Table(child, document)))
    return blocks


def _paragraph(node: Paragraph) -> list[Block]:
    """One paragraph, read for what Word's style says the author meant."""
    style = (node.style.name or "").casefold()
    return paragraph(_pieces(node), _heading_level(style), _item_kind(style))


def _item_kind(style: str) -> str:
    """Whether this paragraph is an item of a list and of which sort."""
    if NUMBER_STYLE_MARKER in style:
        return NUMBERED
    return BULLETED if LIST_STYLE_MARKER in style else ""


def _heading_level(style: str) -> int:
    """The depth a heading style names; nothing where it is not a heading.

    A style is called ``Heading 2`` in English and something else elsewhere,
    so the digit is taken where there is one rather than the name being
    matched. ``Title`` carries no digit and is the top of the document.
    """
    if HEADING_STYLE_MARKER not in style:
        return NO_HEADING
    digits = "".join(character for character in style if character.isdigit())
    return int(digits) if digits else SHALLOWEST_HEADING


def _pieces(node: Paragraph) -> tuple[Piece, ...]:
    """The paragraph's text, in stretches that share a face.

    Runs that share their emphasis are joined before anything is done to them.
    Word splits a run wherever it likes, on a spell check, a language tag or
    an edit somebody made years ago, so one bold phrase commonly arrives as
    several bold runs; marked separately they became ``<strong>imp</strong>``
    followed by ``<strong>ortant</strong>``, which is three elements where the
    author wrote one word. Measured on a real document, three such pairs in
    six pages.

    Nothing is left on either end of the paragraph. An indent typed as spaces
    is presentation in Word, where it moves the first line in a little; there
    is no reason to carry it into a surface that lays the text out itself.
    """
    pieces = [
        Piece("".join(run.text for run in runs), bold, italic)
        for (bold, italic), runs in groupby(node.runs, key=_emphasis_of)
    ]
    kept = [piece for piece in pieces if piece.text]
    return _trimmed(tuple(kept))


def _trimmed(pieces: tuple[Piece, ...]) -> tuple[Piece, ...]:
    """The pieces with the whitespace taken off either end of the paragraph."""
    if not pieces:
        return pieces
    first, last = pieces[0], pieces[-1]
    out = list(pieces)
    out[0] = Piece(first.text.lstrip(), first.bold, first.italic)
    last = out[-1]
    out[-1] = Piece(last.text.rstrip(), last.bold, last.italic)
    return tuple(piece for piece in out if piece.text)


def _emphasis_of(run: Run) -> tuple[bool, bool]:
    """Whether this run is bold and whether it is italic."""
    return bool(run.bold), bool(run.italic)


def _table(node: Table) -> list[Block]:
    """A table of data as a table; a table of layout as its contents.

    Word is used to arrange a page as often as to tabulate anything, so a
    heading beside a photograph and a two column CV are both tables in the
    file. Rendering those as tables is what made a document unreadable:
    measured on a real CV, one layout table of a single row became a row 2550
    characters long, every paragraph of a whole section run together on one
    line, because a cell's own line breaks were collapsed to fit it.

    So a table earns a table by having something to tabulate: more than one
    row and more than one column. Anything else gives up its cells as the
    blocks of text they are, which is what the author put in them.
    """
    rows = list(node.rows)
    if not rows:
        return []
    width = max(len(row.cells) for row in rows)
    if len(rows) < LEAST_TABULAR or width < LEAST_TABULAR:
        return _laid_out(rows)
    return [table([[cell.text for cell in row.cells] for row in rows])]


def _laid_out(rows: list) -> list[Block]:
    """The cells of a layout table, as the blocks of text they hold.

    A cell keeps its own line breaks here rather than being flattened, since
    that is the whole difference between a paragraph and a wall. Merged cells
    are reported once per column they span, so a repeat of what was just said
    is dropped rather than shown twice.
    """
    blocks: list[Block] = []
    said_before = ""
    for row in rows:
        for cell in row.cells:
            for line in cell.text.splitlines():
                said = line.strip()
                if said and said != said_before:
                    blocks.extend(plain(said))
                    said_before = said
    return blocks
