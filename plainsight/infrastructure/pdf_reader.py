"""Reads a PDF back into the document its page was laid out to be.

A PDF describes a page, not a document: it holds glyphs at positions, with no
heading in the file, no paragraph and no list. Asked for its words alone it
gives them up as a wall of text with everything the eye was meant to pick up
thrown away; measured on a real CV, every heading, every bold phrase and every
bullet gone.

So the words are not what is asked for. Every run of text is taken with the
place, the size and the face it was drawn in; `pdf_structure` reads those back
into headings, paragraphs, lists and emphasis. That is a reading of the
page rather than a fact stated by the file, since the file states none; it is
the reading a person does for themselves in a viewer.

A page that cannot be read that way still gives up whatever words it has, so a
failure of the rebuilding costs the layout rather than the page.

Three ways of failing are told apart, because they want different words in
front of a reader: a file that is locked, a file that is not a PDF at all and
a file that holds no text a machine can reach.
"""

from __future__ import annotations

from pypdf import PdfReader

from ..domain.document import DocumentBody, DocumentSummary
from .pdf_structure import Chunk, as_markdown

# Where the text matrix keeps the place it is about to draw at.
X_IN_MATRIX = 4
Y_IN_MATRIX = 5

NOT_A_PDF = "This file could not be read as a PDF."
MISSING_PDF = "This file could not be opened."
LOCKED_PDF = "This PDF is password protected, so its text cannot be read."
NO_TEXT_IN_PDF = (
    "No text could be taken from this PDF. It is most likely a scan, which is "
    "a picture of a page rather than the words on it."
)

# The pages are separated in Markdown, since Markdown is what this reader hands
# over. A row of hyphens drawn as a rule is not that: written under a line of
# text it is the Markdown for a heading, so measured on a real two page CV the
# last line of page one and the words "Page 2" both came back as headings.
PAGE_RULE = "---"


class PdfDocumentReader:
    """A PDF, read as the text it will give up, page by page."""

    def summarise(self, path: str) -> DocumentSummary:
        """Whether it opens and is not locked. A PDF declares no frontmatter.

        No page is extracted here. Opening a PDF reads its cross reference
        table rather than its content, so listing a folder of them costs the
        opening and not the extraction; the extraction happens for the one
        document a reader picks.
        """
        _, failure = _opened(path)
        return DocumentSummary(failure=failure)

    def read_body(self, path: str) -> DocumentBody:
        """Every page's text with its pages marked, else why there is none."""
        reader, failure = _opened(path)
        if reader is None:
            return DocumentBody(failure=failure)
        try:
            pages = [_page(page) for page in reader.pages]
        except Exception:  # noqa: BLE001
            return DocumentBody(failure=NOT_A_PDF)
        text = _joined(pages)
        if not text.strip():
            return DocumentBody(failure=NO_TEXT_IN_PDF)
        return DocumentBody(text=text)


def _rebuilt(page: object) -> str:
    """The page as the document it was laid out to be.

    The extractor is asked for every run of text with its place, its size and
    its face; those are read back into headings, paragraphs, lists and
    emphasis. What that recovers is what a person reading the page in a viewer
    picks up without being told. It is also what asking for the words alone
    throws away: measured on a real CV, a wall of monospace with every heading,
    every bold phrase and every bullet gone.
    """
    chunks: list[Chunk] = []

    def visit(text: str, _cm: object, matrix: list, font: object, size: float) -> None:
        if not text:
            return
        name = str(font.get("/BaseFont", "")) if isinstance(font, dict) else ""
        lowered = name.casefold()
        chunks.append(
            Chunk(
                text=text,
                x=float(matrix[X_IN_MATRIX]),
                y=float(matrix[Y_IN_MATRIX]),
                size=float(size),
                bold="bold" in lowered,
                italic="italic" in lowered or "oblique" in lowered,
            )
        )

    page.extract_text(visitor_text=visit)
    return as_markdown(chunks)


def _page(page: object) -> str:
    """One page, rebuilt as a document; its plain words where that fails.

    The rebuilding reads a page that was laid out for a person. A page that
    cannot be read that way, because it carries no usable font information or
    no content at all, still gives up whatever words it has.
    """
    try:
        rebuilt = _rebuilt(page)
    except Exception:  # noqa: BLE001
        rebuilt = ""
    return rebuilt or _page_text(page)


def _page_text(page: object) -> str:
    """One page's words, for a page that could not be rebuilt as a document.

    The layout is asked for first even here. Measured against a real payslip:
    asked plainly, the extractor returns the words in the order they were
    drawn, so an address block meant for the left of the page and a reference
    meant for the right arrive one after another, each indented by whatever
    happened to precede it. Asked for the layout, the same page comes back with
    the two beside each other where the reader put them. This is the last thing
    tried before a page is given up on, so it keeps what it can.

    The layout reading is the better answer rather than the only one, so any
    failure of it falls back to the plain reading instead of failing the page.
    Measured: a page carrying no content stream at all, which is what a blank
    page in a scan is, comes back from the layout reading as a ``KeyError`` for
    the key that is missing, while the plain reading answers with the empty
    string it should. An older extractor has no layout to offer at all.
    """
    try:
        return page.extract_text(extraction_mode="layout") or ""
    except Exception:  # noqa: BLE001
        return page.extract_text() or ""


def _opened(path: str) -> tuple[PdfReader | None, str]:
    """The reader with no failure; else nothing with a reason.

    A locked file is told apart from a broken one here rather than later. Both
    would otherwise reach a reader as the same shrug; one of the two is
    something they can act on by supplying the file unlocked.

    Anything at all is caught, for the same reason the Word reader catches
    anything: this parses a file somebody else chose; a malformed one can
    raise whatever the parser happens to raise on the way down. A list of the
    types seen so far is a list the next broken file gets to extend.
    """
    try:
        reader = PdfReader(path)
    except OSError:
        return None, MISSING_PDF
    except Exception:  # noqa: BLE001
        return None, NOT_A_PDF
    if reader.is_encrypted:
        return None, LOCKED_PDF
    return reader, ""


def _joined(pages: list[str]) -> str:
    """The pages one after another, each marked off from the one before.

    The marks are there because a PDF's pages are real: text that ran across a
    page break would otherwise read as one sentence that changes subject in the
    middle, with nothing to say why.

    A blank line stands on either side of the rule so that the mark is a mark
    and nothing else. Set against the line above it instead, the rule reads as
    that line's underline and takes it away as a heading.
    """
    parts: list[str] = []
    for number, text in enumerate(pages, start=1):
        if parts:
            parts.append(f"\n\n{PAGE_RULE}\n\n**Page {number}**\n\n")
        parts.append(text)
    return "".join(parts)
