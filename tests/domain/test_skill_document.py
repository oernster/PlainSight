"""Splitting a skill document into its declared fields and its prose."""

from __future__ import annotations

from skillsviewer.domain.skill_document import parse_document

FRONTMATTER = """---
name: prose
description: "Write it correctly first time"
type: habit
---

# Prose

Body text.
"""


def test_a_document_with_frontmatter_gives_up_its_fields() -> None:
    parsed = parse_document(FRONTMATTER)

    assert parsed.name == "prose"
    assert parsed.description == "Write it correctly first time"
    assert parsed.frontmatter["type"] == "habit"


def test_the_body_starts_beneath_the_closing_fence() -> None:
    parsed = parse_document(FRONTMATTER)

    assert parsed.body.startswith("# Prose")
    assert "name: prose" not in parsed.body


def test_a_document_with_no_frontmatter_is_all_body() -> None:
    parsed = parse_document("# Just prose\n\nnothing declared.\n")

    assert parsed.frontmatter == {}
    assert parsed.body.startswith("# Just prose")
    assert parsed.name == ""
    assert parsed.description == ""


def test_an_unclosed_fence_is_left_as_body_rather_than_guessed_at() -> None:
    text = "---\nname: broken\n\n# Body that never closed the block\n"

    parsed = parse_document(text)

    assert parsed.frontmatter == {}
    assert parsed.body == text


def test_an_empty_document_is_all_body() -> None:
    parsed = parse_document("")

    assert parsed.frontmatter == {}
    assert parsed.body == ""


def test_nested_and_unparseable_lines_are_skipped() -> None:
    text = "---\nname: memo\nmetadata:\n  type: user\njust a bare line\n\n---\nBody\n"

    parsed = parse_document(text)

    assert parsed.name == "memo"
    assert "type" not in parsed.frontmatter
    assert "just a bare line" not in parsed.frontmatter


def test_single_and_double_quotes_are_both_dropped() -> None:
    text = "---\nname: 'quoted'\ndescription: \"also quoted\"\n---\nBody\n"

    parsed = parse_document(text)

    assert parsed.name == "quoted"
    assert parsed.description == "also quoted"


def test_a_mismatched_or_short_value_keeps_its_characters() -> None:
    text = '---\nname: "unbalanced\nshort: x\n---\nBody\n'

    parsed = parse_document(text)

    assert parsed.frontmatter["name"] == '"unbalanced'
    assert parsed.frontmatter["short"] == "x"


def test_a_value_that_merely_starts_and_ends_alike_is_left_alone() -> None:
    parsed = parse_document("---\nname: aba\n---\nBody\n")

    assert parsed.frontmatter["name"] == "aba"
