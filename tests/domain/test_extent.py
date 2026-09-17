"""How much of a document there is, counted from its text alone."""

from __future__ import annotations

from plainsight.domain.extent import Extent

THREE_LINES = "one\ntwo\nthree"


def test_the_characters_are_every_character_including_the_line_endings() -> None:
    assert Extent.of(THREE_LINES).characters == len(THREE_LINES)


def test_the_lines_are_the_lines_the_text_is_written_on() -> None:
    assert Extent.of(THREE_LINES).lines == 3


def test_a_closing_line_ending_opens_no_further_line() -> None:
    """Three lines are three whether or not the file ends with a break."""
    assert Extent.of(THREE_LINES + "\n").lines == 3


def test_a_blank_line_is_still_a_line() -> None:
    assert Extent.of("one\n\nthree").lines == 3


def test_text_with_no_break_in_it_is_one_line() -> None:
    assert Extent.of("a wall of words").lines == 1


def test_no_text_is_no_characters_and_no_lines() -> None:
    assert Extent.of("") == Extent(characters=0, lines=0)


def test_two_counts_of_the_same_text_are_the_same_value() -> None:
    """It is a value, so the pane may compare one against another."""
    assert Extent.of(THREE_LINES) == Extent.of(THREE_LINES)
