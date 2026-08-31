"""Giving a wall of text a resting place, without altering one character of it.

The first test is the one that matters: whatever this does, taking the breaks
back out has to return the author's text exactly. Everything after it is about
where the breaks land.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from skillsviewer.domain.passage import (
    GROUP_CHARACTERS,
    MIN_TAIL_CHARACTERS,
    SOFT_BREAK,
    WALL_CHARACTERS,
    soften,
)

SENTENCE = "This is a sentence of a reasonable length that carries some words. "
WALL = SENTENCE * 20
SHORT = "A short paragraph that nobody would call a wall of text."
REAL_SKILLS = Path.home() / ".claude" / "skills"


def breaks(text: str) -> int:
    return text.count(SOFT_BREAK)


def test_taking_the_breaks_out_returns_the_text_exactly() -> None:
    """The guarantee the whole idea rests on."""
    softened = soften(WALL)

    assert breaks(softened) > 0
    assert softened.replace(SOFT_BREAK, "") == WALL


@pytest.mark.parametrize("marker", ["# ", "| ", "> ", "    "])
def test_what_is_not_prose_is_left_exactly_alone(marker: str) -> None:
    """Long enough that it would certainly be broken were it taken for prose."""
    body = marker + WALL

    assert soften(body) == body


def test_an_empty_document_is_left_alone() -> None:
    assert soften("") == ""


def test_a_passage_short_enough_to_read_is_left_alone() -> None:
    """Just under the wall, with a sentence end that would be broken at."""
    body = SENTENCE * 7

    assert len(body) < WALL_CHARACTERS
    assert len(body) > GROUP_CHARACTERS
    assert soften(body) == body


def test_a_wall_is_broken_into_groups_of_whole_sentences() -> None:
    softened = soften(WALL)

    for group in softened.split(SOFT_BREAK):
        assert group.strip().endswith(".")


def test_no_group_is_still_a_wall() -> None:
    for group in soften(WALL).split(SOFT_BREAK):
        assert len(group) < WALL_CHARACTERS


def test_a_fenced_code_block_is_never_broken() -> None:
    body = "```\n" + WALL + "\n```\n"

    assert soften(body) == body


def test_a_break_is_never_placed_inside_a_bracketed_aside() -> None:
    """The aside sits in the middle, where a break would otherwise fall."""
    aside = "(An aside. With a full stop inside it. And a second one. Truly.) "
    body = SENTENCE * 5 + aside + SENTENCE * 5

    softened = soften(body)

    assert SOFT_BREAK in softened
    for group in softened.split(SOFT_BREAK):
        assert group.count("(") == group.count(")")


def test_an_abbreviation_is_not_mistaken_for_the_end_of_a_sentence() -> None:
    """The abbreviation is the first candidate past the size a group is cut at."""
    body = (
        SENTENCE * 4
        + "The gates, e.g. Black and Ruff, run every time. "
        + (SENTENCE * 5)
    )

    softened = soften(body)

    assert SOFT_BREAK in softened
    assert not any(
        group.strip().endswith("e.g.") for group in softened.split(SOFT_BREAK)
    )


def test_an_inventory_with_no_sentence_ends_is_still_broken_up() -> None:
    """The second pass: entries and clauses, since no sentence ever ends."""
    entry = "`thing` (a description of it; with a clause plus more of it), "
    body = "- " + entry * 12 + "`last` (the final one)."

    softened = soften(body)

    assert breaks(softened) > 0
    assert softened.replace(SOFT_BREAK, "") == body


def test_each_list_item_is_weighed_on_its_own() -> None:
    """Several items are several paragraphs already, never one long wall.

    Each is comfortably under the limit while the run of them is far over it,
    so a softener that could not tell one item from the next would break them.
    """
    item = "- " + SENTENCE * 4
    body = "\n".join([item] * 4) + "\n"

    assert len(item) < WALL_CHARACTERS
    assert len(body) > WALL_CHARACTERS
    assert soften(body) == body


def test_a_group_is_not_left_as_a_stranded_fragment() -> None:
    """A break close to the end would leave a line orphaned under the gap.

    Swept across many lengths rather than tried at one, since whether a
    boundary happens to fall near the end depends entirely on the length.
    """
    for sentences in range(8, 40):
        last = soften(SENTENCE * sentences).split(SOFT_BREAK)[-1]

        assert len(last.strip()) >= MIN_TAIL_CHARACTERS


def test_a_break_is_never_placed_inside_an_inline_code_span() -> None:
    """A semicolon inside code is punctuation of the code, not of the prose."""
    entry = "`one; two; three` (an entry with a description of it), "
    body = "- " + entry * 12 + "`last` (the final one)."

    softened = soften(body)

    assert SOFT_BREAK in softened
    for group in softened.split(SOFT_BREAK):
        assert group.count("`") % 2 == 0


def test_the_group_size_is_smaller_than_the_wall_it_breaks() -> None:
    assert GROUP_CHARACTERS < WALL_CHARACTERS


@pytest.mark.skipif(
    not REAL_SKILLS.is_dir(), reason="no skills library on this machine"
)
def test_every_skill_on_this_machine_survives_the_round_trip() -> None:
    """The property held against real documents rather than invented ones."""
    documents = list(REAL_SKILLS.rglob("SKILL.md"))

    for document in documents:
        try:
            text = document.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        assert soften(text).replace(SOFT_BREAK, "") == text

    assert documents
