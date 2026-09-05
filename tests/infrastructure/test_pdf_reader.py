"""Reading a PDF: what comes out of one and the three ways it can fail.

Every PDF here is a real one, written to a real file. What is being tested is
what a PDF gives back, so a stand-in that handed over text on request would be
testing the stand-in.
"""

from __future__ import annotations

from pathlib import Path

from plainsight.domain.document import DocumentKind, Presentation
from plainsight.infrastructure.pdf_reader import (
    LOCKED_PDF,
    NO_TEXT_IN_PDF,
    NOT_A_PDF,
    PdfDocumentReader,
)

from .pdf_fixtures import a_locked_pdf, a_pdf, a_pdf_with_no_text


def written(tmp_path: Path, name: str, data: bytes) -> str:
    (tmp_path / name).write_bytes(data)
    return str(tmp_path / name)


def test_a_pdf_gives_up_the_text_on_its_pages(tmp_path: Path) -> None:
    path = written(tmp_path, "report.pdf", a_pdf([["The opening line."]]))

    body = PdfDocumentReader().read_body(path)

    assert "The opening line." in body.text
    assert not body.failure


def test_every_page_is_marked_off_from_the_one_before(tmp_path: Path) -> None:
    """A PDF's pages are real, so text that ran across a break must say so."""
    path = written(tmp_path, "two.pdf", a_pdf([["First page."], ["Second page."]]))

    body = PdfDocumentReader().read_body(path)

    assert "First page." in body.text
    assert "Second page." in body.text
    assert "Page 2" in body.text
    assert body.text.index("First page.") < body.text.index("Second page.")


def test_a_single_page_is_not_given_a_page_marker(tmp_path: Path) -> None:
    """There is nothing to mark it off from, so the mark would be noise."""
    path = written(tmp_path, "one.pdf", a_pdf([["Only page."]]))

    assert "Page 1" not in PdfDocumentReader().read_body(path).text


def test_a_summarised_pdf_declares_nothing_and_reports_nothing(
    tmp_path: Path,
) -> None:
    """A listing opens the file; it does not extract a single page of it."""
    path = written(tmp_path, "report.pdf", a_pdf([["Text."]]))

    summary = PdfDocumentReader().summarise(path)

    assert summary.declared_fields == ()
    assert summary.declared_name == ""
    assert not summary.failure


def test_a_locked_pdf_says_it_is_locked_rather_than_shrugging(
    tmp_path: Path,
) -> None:
    """A reader can act on this one by supplying the file unlocked."""
    path = written(tmp_path, "locked.pdf", a_locked_pdf())

    assert PdfDocumentReader().summarise(path).failure == LOCKED_PDF
    assert PdfDocumentReader().read_body(path).failure == LOCKED_PDF


def test_a_pdf_holding_no_text_says_it_is_most_likely_a_scan(
    tmp_path: Path,
) -> None:
    """A picture of a page is the commonest reason and the least obvious one."""
    path = written(tmp_path, "scan.pdf", a_pdf_with_no_text())

    body = PdfDocumentReader().read_body(path)

    assert body.failure == NO_TEXT_IN_PDF
    assert not body.text


def test_a_file_that_is_not_a_pdf_at_all_says_so(tmp_path: Path) -> None:
    path = written(tmp_path, "notreally.pdf", b"this is not a PDF at all")

    assert PdfDocumentReader().summarise(path).failure == NOT_A_PDF
    assert PdfDocumentReader().read_body(path).failure == NOT_A_PDF


def test_a_pdf_that_is_not_there_says_so(tmp_path: Path) -> None:
    absent = str(tmp_path / "absent.pdf")

    assert PdfDocumentReader().summarise(absent).failure
    assert PdfDocumentReader().read_body(absent).failure


def test_a_pdf_is_shown_as_typed_rather_than_laid_out() -> None:
    """Text out of a PDF carries the page's line breaks, not the author's.

    Softening it would run the columns of a two column page together, which is
    why this kind is presented verbatim rather than reflowed.
    """
    assert DocumentKind.PDF.presentation is Presentation.AS_TYPED
    assert not DocumentKind.PDF.reflows
    assert not DocumentKind.PDF.declares_fields
