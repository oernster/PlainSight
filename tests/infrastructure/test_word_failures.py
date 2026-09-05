"""Reading a Word document that will not be read; listing one too.

The other half of the Word reader lives in ``test_word_reader.py``, which is
about what a document BECOMES. This file is about the three ways it can give
nothing back, plus what a listing knows without pulling the document apart.
The two are separated because they exercise different halves of the reader and
share nothing but the way a file is written.
"""

from __future__ import annotations

import zipfile
from pathlib import Path

from plainsight.domain.document import DocumentKind, Presentation
from plainsight.infrastructure.word_reader import (
    EMPTY_WORD_FILE,
    NOT_A_WORD_FILE,
    WordDocumentReader,
)

from .test_word_reader import a_word_file


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


def test_a_word_document_arrives_as_the_html_its_reader_made_of_it() -> None:
    """So the renderer hands it over untouched rather than rewriting it."""
    assert DocumentKind.WORD.presentation is Presentation.ALREADY_HTML
    assert not DocumentKind.WORD.reflows
    assert not DocumentKind.WORD.declares_fields
