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
from plainsight.infrastructure.renderer import DocumentHtmlRenderer

from .pdf_fixtures import (
    a_locked_pdf,
    a_pdf,
    a_pdf_with_no_text,
    a_pdf_with_two_columns,
)


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


def test_the_page_mark_does_not_turn_the_line_above_it_into_a_heading(
    tmp_path: Path,
) -> None:
    """The mark is Markdown, because Markdown is what this reader hands over.

    A rule set directly against the line above it is the Markdown for a
    heading rather than for a rule. Measured on a real two page CV: the last
    line of page one and the words "Page 2" both came back as headings.
    """
    path = written(
        tmp_path, "two.pdf", a_pdf([["The last line of the first page."], ["Second."]])
    )

    text = PdfDocumentReader().read_body(path).text
    html = DocumentHtmlRenderer().render(text, DocumentKind.PDF)

    assert "<h1" not in html
    assert "<h2" not in html
    assert "<hr" in html


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


def test_words_side_by_side_on_the_page_stay_side_by_side(tmp_path: Path) -> None:
    """What a form says, it says by where it puts the words.

    Read plainly, two things drawn beside each other come back one after the
    other, so an address meant for the left of a payslip and a reference meant
    for the right arrive as two unrelated lines. Rebuilding the page keeps them
    on the line they were on, with the gutter between them put back as a space:
    joined literally they read as one run-together word.
    """
    path = written(
        tmp_path, "form.pdf", a_pdf_with_two_columns("Employee name", "Reference")
    )

    text = PdfDocumentReader().read_body(path).text

    together = [
        line
        for line in text.splitlines()
        if "Employee name" in line and "Reference" in line
    ]
    assert together, text
    assert together[0].index("Employee name") < together[0].index("Reference")
    assert "nameReference" not in together[0]


def test_a_pdf_is_laid_out_because_its_reader_hands_over_markdown() -> None:
    """The line breaks a PDF gives up are the page's, so they are not kept.

    Its reader rebuilds the page as a document before the domain ever sees it,
    so what arrives is Markdown exactly as a Word document's does, rather than
    the words in the order the page happened to draw them.
    """
    assert DocumentKind.PDF.presentation is Presentation.LAID_OUT
    assert DocumentKind.PDF.reflows
    assert not DocumentKind.PDF.declares_fields
