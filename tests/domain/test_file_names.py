"""File names from foreign text: safe on Windows, inside their folder, unique."""

from __future__ import annotations

import pytest

from plainsight.domain.file_names import (
    MAX_STEM_LENGTH,
    is_safe_file_name,
    release_file_stem,
    safe_segment,
    unique_name,
)

A_MOMENT = "2026-09-29T10:15:00Z"
WINDOWS_FORBIDDEN = '<>:"/\\|?*'


def test_a_semantic_version_tag_reads_as_itself_after_its_date() -> None:
    assert release_file_stem(A_MOMENT, "v1.4.0") == "2026-09-29_v1.4.0"


def test_an_undated_release_says_so_in_its_name() -> None:
    assert release_file_stem("", "v1.4.0") == "undated_v1.4.0"


def test_a_slash_in_a_tag_names_no_directory() -> None:
    stem = release_file_stem(A_MOMENT, "release/2026")

    assert "/" not in stem
    assert stem == "2026-09-29_release_2026"


@pytest.mark.parametrize("character", list(WINDOWS_FORBIDDEN) + ["\x00", "\x1f"])
def test_every_character_windows_refuses_is_replaced(character: str) -> None:
    stem = safe_segment(f"a{character}b")

    assert stem == "a_b"


@pytest.mark.parametrize(
    "hostile", ["../../etc/passwd", "..\\..\\Windows", "..", ".", " . . ", "/"]
)
def test_an_attempt_to_climb_out_stays_one_harmless_segment(hostile: str) -> None:
    stem = safe_segment(hostile)

    assert "/" not in stem and "\\" not in stem
    assert stem.strip(". ") != ""


@pytest.mark.parametrize("name", ["CON", "prn", "Aux", "nul", "COM1", "lpt9", "COM¹"])
def test_a_reserved_device_name_is_moved_aside(name: str) -> None:
    assert safe_segment(name) == f"_{name}"


def test_a_reserved_name_with_a_suffix_is_moved_aside_as_well() -> None:
    assert safe_segment("con.txt") == "_con.txt"


def test_a_name_merely_starting_like_a_device_is_left_alone() -> None:
    assert safe_segment("console") == "console"


def test_trailing_dots_and_spaces_windows_would_drop_are_removed() -> None:
    assert safe_segment("v1.0. . ") == "v1.0"


def test_unicode_is_kept_and_composed_one_way() -> None:
    decomposed = "café \U0001f680"

    assert safe_segment(decomposed) == "café \U0001f680"


def test_a_very_long_tag_is_cut_to_the_cap() -> None:
    stem = release_file_stem(A_MOMENT, "v" * 500)

    assert len(stem) < MAX_STEM_LENGTH
    assert stem.startswith("2026-09-29_vvv")


def test_names_colliding_after_cleaning_are_told_apart() -> None:
    taken: set[str] = set()

    first = unique_name(release_file_stem(A_MOMENT, "a/b"), taken)
    second = unique_name(release_file_stem(A_MOMENT, "a:b"), taken)
    third = unique_name(release_file_stem(A_MOMENT, "A|B"), taken)

    assert first == "2026-09-29_a_b.md"
    assert second == "2026-09-29_a_b_2.md"
    assert third == "2026-09-29_A_B_3.md"


def test_a_name_made_unique_at_the_cap_still_reads_back_as_safe() -> None:
    taken: set[str] = set()
    stem = release_file_stem(A_MOMENT, "x" * 500)
    unique_name(stem, taken)

    second = unique_name(stem, taken)

    assert is_safe_file_name(second)


@pytest.mark.parametrize(
    "name", ["../x.md", "a/b.md", "notes.txt", ".md", "CON.md", "x. .md", ""]
)
def test_a_name_this_could_not_have_made_is_not_believed(name: str) -> None:
    assert not is_safe_file_name(name)


def test_a_name_this_made_is_believed() -> None:
    assert is_safe_file_name("2026-09-29_v1.4.0.md")
