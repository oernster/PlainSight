"""One reader, reading one kind: what it declares, then its text on demand."""

from __future__ import annotations

from pathlib import Path

from plainsight.domain.document import DocumentKind
from plainsight.infrastructure.document_reader import (
    EMPTY_MARKDOWN_TEXT,
    EMPTY_TEXT,
    MISSING_TEXT,
    UNREADABLE_TEXT,
    TextDocumentReader,
)

A_SKILL = "---\nname: prose\ndescription: writing\n---\n\n# Prose\n\nBody.\n"


def markdown() -> TextDocumentReader:
    return TextDocumentReader(DocumentKind.MARKDOWN)


def plain_text() -> TextDocumentReader:
    return TextDocumentReader(DocumentKind.PLAIN_TEXT)


def test_a_summary_carries_what_the_document_declares(tmp_path: Path) -> None:
    written = tmp_path / "SKILL.md"
    written.write_text(A_SKILL, encoding="utf-8")

    summary = markdown().summarise(str(written))

    assert summary.declared_name == "prose"
    assert summary.description == "writing"
    assert summary.declared_fields == (("name", "prose"), ("description", "writing"))
    assert not summary.failure


def test_a_summary_carries_no_body(tmp_path: Path) -> None:
    """The whole reason the two halves are apart, said as an assertion."""
    written = tmp_path / "SKILL.md"
    written.write_text(A_SKILL, encoding="utf-8")

    summary = markdown().summarise(str(written))

    assert not hasattr(summary, "text")
    assert not hasattr(summary, "body")


def test_the_body_arrives_without_the_fields_the_summary_took(tmp_path: Path) -> None:
    written = tmp_path / "SKILL.md"
    written.write_text(A_SKILL, encoding="utf-8")

    body = markdown().read_body(str(written))

    assert body.text.startswith("# Prose")
    assert "description: writing" not in body.text
    assert not body.failure


def test_a_reader_told_it_reads_plain_text_declares_nothing(tmp_path: Path) -> None:
    """The kind is what settles whether a leading fence is a block of fields."""
    written = tmp_path / "notes.txt"
    written.write_text(A_SKILL, encoding="utf-8")

    summary = plain_text().summarise(str(written))

    assert summary.declared_fields == ()
    assert summary.declared_name == ""
    assert plain_text().read_body(str(written)).text.startswith("---")


def test_a_file_that_is_not_utf_8_says_so_in_both_halves(tmp_path: Path) -> None:
    written = tmp_path / "broken.md"
    written.write_bytes(b"\xff\xfe\x00binary")

    assert markdown().summarise(str(written)).failure == UNREADABLE_TEXT
    assert markdown().read_body(str(written)).failure == UNREADABLE_TEXT


def test_a_file_that_is_not_there_says_so_in_both_halves(tmp_path: Path) -> None:
    absent = str(tmp_path / "absent.md")

    assert markdown().summarise(absent).failure == MISSING_TEXT
    assert markdown().read_body(absent).failure == MISSING_TEXT


def test_an_empty_markdown_file_names_its_frontmatter(tmp_path: Path) -> None:
    written = tmp_path / "SKILL.md"
    written.write_text("---\nname: hollow\n---\n\n", encoding="utf-8")

    assert markdown().summarise(str(written)).failure == EMPTY_MARKDOWN_TEXT


def test_an_empty_text_file_gives_the_plainer_reason(tmp_path: Path) -> None:
    """It has no frontmatter to be empty beneath, so it must not say it has."""
    written = tmp_path / "notes.txt"
    written.write_text("   \n", encoding="utf-8")

    assert plain_text().summarise(str(written)).failure == EMPTY_TEXT


def test_an_empty_file_still_gives_up_its_body_without_complaint(
    tmp_path: Path,
) -> None:
    """Emptiness is a thing to report in a listing, not a failure to read.

    The distinction matters for the reader that comes next: a file that is
    there and holds nothing is not the same as one that could not be opened;
    only the second is a reason to stop.
    """
    written = tmp_path / "notes.txt"
    written.write_text("   \n", encoding="utf-8")

    body = plain_text().read_body(str(written))

    assert not body.failure
    assert not body.text.strip()
