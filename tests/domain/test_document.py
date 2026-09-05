"""What a document is, what kind it is and what it says about itself."""

from __future__ import annotations

import pytest

from plainsight.domain.document import (
    HEADER_FIELD_LIMIT,
    Document,
    DocumentKind,
    InvalidDocument,
    kind_of,
)


def a_document(**changed: object) -> Document:
    """A readable Markdown document, with anything the test cares about changed."""
    fields = {
        "name": "SKILL.md",
        "path": "/skills/prose/SKILL.md",
        "kind": DocumentKind.MARKDOWN,
        "body": "The body.",
    }
    fields.update(changed)
    return Document(**fields)  # type: ignore[arg-type]


def test_every_kind_carries_its_own_suffix() -> None:
    assert DocumentKind.MARKDOWN.suffix == ".md"
    assert DocumentKind.PLAIN_TEXT.suffix == ".txt"


def test_only_markdown_declares_fields_and_reflows() -> None:
    """Plain text keeps its own line breaks and its own opening lines.

    Both properties are asserted here rather than assumed equal: they answer
    different questions and a kind added later may separate them.
    """
    assert DocumentKind.MARKDOWN.declares_fields
    assert DocumentKind.MARKDOWN.reflows
    assert not DocumentKind.PLAIN_TEXT.declares_fields
    assert not DocumentKind.PLAIN_TEXT.reflows


@pytest.mark.parametrize(
    ("file_name", "expected"),
    [
        ("SKILL.md", DocumentKind.MARKDOWN),
        ("NOTES.MD", DocumentKind.MARKDOWN),
        ("shopping.txt", DocumentKind.PLAIN_TEXT),
        ("archive.tar.md", DocumentKind.MARKDOWN),
    ],
)
def test_a_known_suffix_names_its_kind(file_name: str, expected: DocumentKind) -> None:
    assert kind_of(file_name) is expected


@pytest.mark.parametrize(
    "file_name",
    ["photo.png", "README", "", ".md", ".txt", "notes."],
)
def test_anything_else_is_not_a_document(file_name: str) -> None:
    """A name that is nothing but a suffix has no stem and is not a file we read."""
    assert kind_of(file_name) is None


def test_a_document_needs_a_name() -> None:
    with pytest.raises(InvalidDocument):
        a_document(name="   ")


def test_a_document_needs_a_path() -> None:
    with pytest.raises(InvalidDocument):
        a_document(path="")


def test_a_document_needs_a_body_or_a_failure() -> None:
    with pytest.raises(InvalidDocument):
        a_document(body="  ")


def test_a_failure_stands_in_for_a_body() -> None:
    """An unreadable file is still listed, so it is still a document."""
    document = a_document(body="", failure="Could not be read.")

    assert not document.is_readable
    assert document.failure == "Could not be read."


def test_a_document_that_read_cleanly_is_readable() -> None:
    assert a_document().is_readable


def test_the_title_is_the_declared_name_where_there_is_one() -> None:
    assert a_document(declared_name="prose").title == "prose"


def test_the_title_falls_back_to_the_file_name() -> None:
    """A document declaring nothing still has to be called something."""
    assert a_document(declared_name="   ").title == "SKILL.md"


def test_documents_order_by_file_name_case_insensitively() -> None:
    assert a_document(name="Alpha.md").sort_key == "alpha.md"


def test_the_two_fields_already_shown_are_left_out_of_the_rest() -> None:
    document = a_document(
        declared_fields=(("name", "prose"), ("description", "how"), ("model", "opus"))
    )

    assert document.header_fields == (("model", "opus"),)


def test_a_short_field_reads_as_a_header_row() -> None:
    document = a_document(declared_fields=(("model", "x" * HEADER_FIELD_LIMIT),))

    assert document.header_fields == (("model", "x" * HEADER_FIELD_LIMIT),)
    assert document.long_fields == ()


def test_an_oversized_field_is_given_a_section_of_its_own() -> None:
    """Measured at eleven thousand characters on one line in a real library."""
    long = "x" * (HEADER_FIELD_LIMIT + 1)
    document = a_document(declared_fields=(("model", long),))

    assert document.header_fields == ()
    assert document.long_fields == (("model", long),)
