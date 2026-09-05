"""Reads a PDF as the plain text that can be got out of it, saying so plainly.

A PDF describes a page, not a document: it holds glyphs at positions, so the
text pulled back out is a reconstruction rather than the thing the author
wrote. Two columns come back interleaved, a table comes back as its cells in
whatever order they were drawn; a page that is a photograph of text comes
back as nothing at all. None of that is a defect to be fixed here; it is what
the format is; the honest answer is to show what came out, marked as the
plain text it is, rather than to dress it up as a document.

So a PDF is presented verbatim. Softening it would run the columns of a two
column page together, since the line breaks that came out are the page's own.

Three ways of failing are told apart, because they want different words in
front of a reader: a file that is locked, a file that is not a PDF at all and
a file that holds no text a machine can reach.
"""

from __future__ import annotations

from pypdf import PdfReader

from ..domain.document import DocumentBody, DocumentSummary

NOT_A_PDF = "This file could not be read as a PDF."
MISSING_PDF = "This file could not be opened."
LOCKED_PDF = "This PDF is password protected, so its text cannot be read."
NO_TEXT_IN_PDF = (
    "No text could be taken from this PDF. It is most likely a scan, which is "
    "a picture of a page rather than the words on it."
)

PAGE_SEPARATOR_RULE = "-"
PAGE_SEPARATOR_WIDTH = 40


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
            pages = [_page_text(page) for page in reader.pages]
        except Exception:  # noqa: BLE001
            return DocumentBody(failure=NOT_A_PDF)
        text = _joined(pages)
        if not text.strip():
            return DocumentBody(failure=NO_TEXT_IN_PDF)
        return DocumentBody(text=text)


def _page_text(page: object) -> str:
    """One page's text, keeping where on the page the words sat.

    Measured against a real payslip: asked plainly, the extractor returns the
    words in the order they were drawn, so an address block meant for the left
    of the page and a reference meant for the right arrive one after another,
    each indented by whatever happened to precede it. Asked for the layout, the
    same page comes back with the two beside each other where the reader put
    them.

    Anything a document made of columns, a form or a table has to say is said
    by where it sits, so throwing that away leaves the words and loses the
    document. Lines get long, which is why the reading pane lets a page of this
    kind be as wide as it is rather than folding it.

    Reading the layout is the better answer rather than the only one, so any
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
    """
    rule = PAGE_SEPARATOR_RULE * PAGE_SEPARATOR_WIDTH
    parts: list[str] = []
    for number, text in enumerate(pages, start=1):
        if parts:
            parts.append(f"\n{rule}\nPage {number}\n{rule}\n\n")
        parts.append(text)
    return "".join(parts)
