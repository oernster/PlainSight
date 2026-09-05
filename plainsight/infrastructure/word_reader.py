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

from itertools import groupby
from pathlib import Path

import docx
from docx.document import Document as WordDocument
from docx.oxml.ns import qn
from docx.table import Table
from docx.text.paragraph import Paragraph
from docx.text.run import Run

from ..domain.document import DocumentBody, DocumentSummary

NOT_A_WORD_FILE = "This file could not be read as a Word document."
MISSING_WORD_FILE = "This file could not be opened."
EMPTY_WORD_FILE = "This Word document holds no text."

HEADING_PREFIX = "#"
BOLD = "**"
ITALIC = "*"
# A table earns Markdown by having something to tabulate: rows AND columns.
LEAST_TABULAR = 2
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
    """One paragraph as Markdown; empty where it holds nothing to show.

    A paragraph gives up its text with nothing left on either end of it. An
    indent typed as spaces is presentation in Word, where it moves the first
    line in a little; the same spaces are syntax in Markdown, where four of
    them make a block of code. Measured on a real CV: three paragraphs of the
    profile were typed with a four space indent and arrived as a wall of
    monospace, clipped at the right edge with a scrollbar under it, while
    every paragraph around them read normally.
    """
    text = _runs(paragraph).strip()
    if not text:
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
    """The paragraph's text, keeping the emphasis Markdown can say.

    Runs that share their emphasis are joined before the marks go on. Word
    splits a run wherever it likes, on a spell check, a language tag or an
    edit somebody made years ago, so one bold phrase commonly arrives as
    several bold runs. Marking each of them separately produced ``**imp****
    ortant**``, which is not emphasis at all: it renders as the asterisks
    themselves. Measured on a real document, three such pairs in six pages.
    """
    pieces: list[str] = []
    for emphasis, runs in groupby(paragraph.runs, key=_emphasis_of):
        text = "".join(run.text for run in runs)
        if text:
            pieces.append(_emphasised(text, emphasis))
    return "".join(pieces)


def _emphasis_of(run: Run) -> tuple[bool, bool]:
    """Whether this run is bold and whether it is italic."""
    return bool(run.bold), bool(run.italic)


def _emphasised(text: str, emphasis: tuple[bool, bool]) -> str:
    """The text with its marks on, the spaces around it left outside them.

    Markdown will not open emphasis on a space, so a run beginning or ending
    with one has to keep it outside the marks; inside, the marks show as
    themselves and the emphasis is lost with them.
    """
    bold, italic = emphasis
    if not (bold or italic) or not text.strip():
        return text
    lead = text[: len(text) - len(text.lstrip())]
    trail = text[len(text.rstrip()) :]
    marks = f"{BOLD if bold else ''}{ITALIC if italic else ''}"
    return f"{lead}{marks}{text.strip()}{marks}{trail}"


def _table(table: Table) -> str:
    """A table of data as a Markdown table; a table of layout as its contents.

    Word is used to arrange a page as often as to tabulate anything, so a
    heading beside a photograph and a two column CV are both tables in the
    file. Rendering those as tables is what made a document unreadable:
    measured on a real CV, one layout table of a single row became a Markdown
    row 2550 characters long, every paragraph of a whole section run together
    on one line, because a cell's own line breaks were collapsed to fit it.

    So a table earns Markdown by having something to tabulate: more than one
    row and more than one column. Anything else gives up its cells as the
    blocks of text they are, which is what the author put in them.
    """
    rows = list(table.rows)
    if not rows:
        return ""
    width = max(len(row.cells) for row in rows)
    if len(rows) < LEAST_TABULAR or width < LEAST_TABULAR:
        return _laid_out(rows)
    cells = [[_flat(cell.text) for cell in row.cells] for row in rows]
    lines = [_row(cells[0], width), _row([_RULE] * width, width)]
    lines.extend(_row(row, width) for row in cells[1:])
    return "\n".join(lines)


def _laid_out(rows: list) -> str:
    """The cells of a layout table, as the blocks of text they hold.

    A cell keeps its own line breaks here rather than being flattened, since
    that is the whole difference between a paragraph and a wall. Merged cells
    are reported once per column they span, so a repeat of what was just said
    is dropped rather than shown twice.
    """
    blocks: list[str] = []
    for row in rows:
        for cell in row.cells:
            for line in cell.text.splitlines():
                said = line.strip()
                if said and (not blocks or blocks[-1] != said):
                    blocks.append(said)
    return "\n\n".join(blocks)


def _flat(text: str) -> str:
    """A cell's text on one line, which is all a Markdown table row allows."""
    return " ".join(text.split())


_RULE = "---"


def _row(cells: list[str], width: int) -> str:
    """One table row, padded to the width of the widest row in the table."""
    padded = list(cells) + [""] * (width - len(cells))
    return f"{TABLE_EDGE} " + f" {TABLE_EDGE} ".join(padded) + f" {TABLE_EDGE}"
