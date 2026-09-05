"""Reading a Word document: what survives the crossing into Markdown.

Every document here is a real one written by python-docx, because what is being
tested is what comes back out of the format.
"""

from __future__ import annotations

import zipfile
from pathlib import Path

import docx

from plainsight.domain.document import DocumentKind, Presentation
from plainsight.infrastructure.word_reader import (
    EMPTY_WORD_FILE,
    NOT_A_WORD_FILE,
    WordDocumentReader,
)


def a_word_file(tmp_path: Path, build) -> str:
    """A real .docx on disk, built by whatever the test wants in it."""
    document = docx.Document()
    build(document)
    path = tmp_path / "report.docx"
    document.save(str(path))
    return str(path)


def test_a_heading_crosses_as_a_markdown_heading(tmp_path: Path) -> None:
    path = a_word_file(tmp_path, lambda d: d.add_heading("The Title", level=1))

    body = WordDocumentReader().read_body(path)

    assert "# The Title" in body.text
    assert not body.failure


def test_a_deeper_heading_keeps_its_depth(tmp_path: Path) -> None:
    """Taken from the digit in the style name, so it survives a translation."""

    def build(document) -> None:
        document.add_heading("Top", level=1)
        document.add_heading("Under it", level=3)

    body = WordDocumentReader().read_body(a_word_file(tmp_path, build))

    assert "# Top" in body.text
    assert "### Under it" in body.text


def test_paragraphs_come_across_in_order(tmp_path: Path) -> None:
    def build(document) -> None:
        document.add_paragraph("First paragraph.")
        document.add_paragraph("Second paragraph.")

    text = WordDocumentReader().read_body(a_word_file(tmp_path, build)).text

    assert text.index("First paragraph.") < text.index("Second paragraph.")


def test_a_bulleted_list_crosses_as_a_bulleted_list(tmp_path: Path) -> None:
    def build(document) -> None:
        document.add_paragraph("Milk", style="List Bullet")
        document.add_paragraph("Eggs", style="List Bullet")

    text = WordDocumentReader().read_body(a_word_file(tmp_path, build)).text

    assert "- Milk" in text
    assert "- Eggs" in text


def test_a_numbered_list_crosses_as_a_numbered_list(tmp_path: Path) -> None:
    def build(document) -> None:
        document.add_paragraph("Step one", style="List Number")

    assert (
        "1. Step one"
        in WordDocumentReader().read_body(a_word_file(tmp_path, build)).text
    )


def test_bold_and_italic_survive(tmp_path: Path) -> None:
    def build(document) -> None:
        paragraph = document.add_paragraph()
        paragraph.add_run("plain ")
        paragraph.add_run("strong").bold = True
        paragraph.add_run(" and ")
        paragraph.add_run("leaning").italic = True

    text = WordDocumentReader().read_body(a_word_file(tmp_path, build)).text

    assert "**strong**" in text
    assert "*leaning*" in text


def test_a_table_crosses_as_a_markdown_table(tmp_path: Path) -> None:
    def build(document) -> None:
        table = document.add_table(rows=2, cols=2)
        table.cell(0, 0).text = "Key"
        table.cell(0, 1).text = "Value"
        table.cell(1, 0).text = "a"
        table.cell(1, 1).text = "1"

    text = WordDocumentReader().read_body(a_word_file(tmp_path, build)).text

    assert "| Key | Value |" in text
    assert "| --- | --- |" in text
    assert "| a | 1 |" in text


def test_a_table_lands_between_the_paragraphs_it_sits_between(
    tmp_path: Path,
) -> None:
    """Read off two separate lists, a table lands after every paragraph.

    python-docx exposes paragraphs and tables as two collections, each in
    document order only within itself. Walking the body's own XML is what keeps
    a table where its author put it.
    """

    def build(document) -> None:
        document.add_paragraph("Before the table.")
        document.add_table(rows=1, cols=1).cell(0, 0).text = "In the table"
        document.add_paragraph("After the table.")

    text = WordDocumentReader().read_body(a_word_file(tmp_path, build)).text

    assert text.index("Before the table.") < text.index("In the table")
    assert text.index("In the table") < text.index("After the table.")


def test_an_empty_paragraph_leaves_no_gap_behind_it(tmp_path: Path) -> None:
    def build(document) -> None:
        document.add_paragraph("Something.")
        document.add_paragraph("")
        document.add_paragraph("Something else.")

    text = WordDocumentReader().read_body(a_word_file(tmp_path, build)).text

    assert "\n\n\n" not in text


def test_a_word_document_holding_no_text_says_so(tmp_path: Path) -> None:
    path = a_word_file(tmp_path, lambda d: None)

    body = WordDocumentReader().read_body(path)

    assert body.failure == EMPTY_WORD_FILE
    assert not body.text


def test_a_file_that_is_not_a_word_document_says_so(tmp_path: Path) -> None:
    """A .docx is a zip, so anything that is not one fails at the container."""
    path = tmp_path / "notreally.docx"
    path.write_bytes(b"this is not a Word document")

    assert WordDocumentReader().summarise(str(path)).failure == NOT_A_WORD_FILE
    assert WordDocumentReader().read_body(str(path)).failure == NOT_A_WORD_FILE


def test_a_zip_that_is_not_a_word_document_says_so(tmp_path: Path) -> None:
    """It opens as a container and then turns out to hold something else.

    A different complaint from the library than a file that is not a zip at
    all, so it is worth its own test: read in the installed source, this is
    the path that raises rather than the one that fails to open.
    """
    path = tmp_path / "spreadsheet.docx"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")

    assert WordDocumentReader().read_body(str(path)).failure == NOT_A_WORD_FILE


def test_a_word_document_that_is_not_there_says_so(tmp_path: Path) -> None:
    absent = str(tmp_path / "absent.docx")

    assert WordDocumentReader().summarise(absent).failure
    assert WordDocumentReader().read_body(absent).failure


def test_a_summarised_word_document_declares_nothing(tmp_path: Path) -> None:
    """A listing opens the container; it does not pull the document apart."""
    path = a_word_file(tmp_path, lambda d: d.add_paragraph("Text."))

    summary = WordDocumentReader().summarise(path)

    assert summary.declared_fields == ()
    assert summary.declared_name == ""
    assert not summary.failure


def test_a_word_document_is_laid_out_because_its_reader_made_it_markdown() -> None:
    assert DocumentKind.WORD.presentation is Presentation.LAID_OUT
    assert DocumentKind.WORD.reflows
    assert not DocumentKind.WORD.declares_fields
