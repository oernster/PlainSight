"""Reading a page's glyphs back into the document it was laid out to be.

Every case here is stated as the chunks a page draws, because that is what the
extractor hands over and it is the only thing this module is given. The numbers
are page points, with y counted up from the foot of the page as a PDF counts
it, so a larger y is higher up.
"""

from __future__ import annotations

from plainsight.infrastructure.pdf_structure import (
    Chunk,
    as_markdown,
    body_size_of,
    lines_of,
)

BODY = 10.0
HEADING = 17.0
LINE_HEIGHT = 12.0
TOP = 700.0


def run(
    text: str,
    x: float = 72.0,
    y: float = TOP,
    size: float = BODY,
    bold: bool = False,
    italic: bool = False,
) -> Chunk:
    return Chunk(text=text, x=x, y=y, size=size, bold=bold, italic=italic)


def down(rows: list[list[Chunk]]) -> list[Chunk]:
    """The rows placed one under another, so a caller states only the text."""
    return [
        Chunk(
            chunk.text,
            chunk.x,
            TOP - number * LINE_HEIGHT,
            chunk.size,
            chunk.bold,
            chunk.italic,
        )
        for number, row in enumerate(rows)
        for chunk in row
    ]


def test_consecutive_lines_of_body_text_become_one_paragraph() -> None:
    """A line break inside a PDF paragraph is a fact about the page width."""
    chunks = down([[run("The first half of a sentence")], [run("and its second.")]])

    assert as_markdown(chunks) == "The first half of a sentence and its second."


def test_a_line_larger_than_the_body_is_a_heading() -> None:
    chunks = down(
        [
            [run("Experience", size=HEADING)],
            [run("What was done there.")],
            [run("More of what was done there.")],
        ]
    )

    assert as_markdown(chunks) == (
        "# Experience\n\nWhat was done there. More of what was done there."
    )


def test_heading_depth_follows_size_from_the_largest_down() -> None:
    """The ordering a reader takes from the page without being told."""
    chunks = down(
        [
            [run("Title", size=24.0)],
            [run("Section", size=HEADING)],
            [run("Body text sits under both of them.")],
            [run("It carries on for a second line.")],
            [run("It carries on for a third.")],
            [run("It carries on for a fourth.")],
        ]
    )

    assert as_markdown(chunks).startswith("# Title\n\n## Section\n\n")


def test_a_page_of_nothing_but_headings_has_none() -> None:
    """A form has no dominant body size, so every line would qualify.

    Read without this guard a real payslip came back as a stack of headings
    with every line of it shouting.
    """
    chunks = down(
        [
            [run("Employee", size=14.0)],
            [run("Reference", size=16.0)],
            [run("Period", size=18.0)],
            [run("Tax code", size=20.0)],
        ]
    )

    assert "#" not in as_markdown(chunks)


def test_a_line_opening_with_a_bullet_is_an_item() -> None:
    chunks = down([[run("• Did a thing")], [run("• Did another thing")]])

    assert as_markdown(chunks) == "- Did a thing\n\n- Did another thing"


def test_the_second_line_of_a_wrapped_item_stays_in_that_item() -> None:
    """An item wraps like any other text, so its second line carries no bullet.

    Started as a paragraph of its own it broke every wrapped item on the page
    in two.
    """
    chunks = down(
        [[run("• An item long enough to")], [run("run on to a second line.")]]
    )

    assert as_markdown(chunks) == "- An item long enough to run on to a second line."


def test_a_wider_gap_than_usual_starts_a_new_block() -> None:
    """Measured on a real CV: 11.2 points within a paragraph, 14.3 between."""
    chunks = [
        run("The end of one paragraph.", y=TOP),
        run("The start of the next.", y=TOP - LINE_HEIGHT),
        run("Still the second one.", y=TOP - 2 * LINE_HEIGHT),
        run("A paragraph on its own.", y=TOP - 4 * LINE_HEIGHT),
    ]

    assert as_markdown(chunks) == (
        "The end of one paragraph. The start of the next. Still the second one."
        "\n\nA paragraph on its own."
    )


def test_a_line_wholly_in_the_bold_face_is_one_emphasis() -> None:
    """A run of separately marked words reads as a stutter of asterisks."""
    chunks = [run("Head", bold=True), run("line here", x=95.0, bold=True)]

    assert as_markdown(chunks) == "**Headline here**"


def test_emphasis_inside_a_line_marks_only_the_words_it_covers() -> None:
    chunks = [
        run("Ordinary text then "),
        run("something bold", x=170.0, bold=True),
        run(" and the rest.", x=250.0),
    ]

    assert as_markdown(chunks) == "Ordinary text then **something bold** and the rest."


def test_an_italic_run_is_marked_as_italic() -> None:
    chunks = [run("A word "), run("stressed", x=120.0, italic=True)]

    assert as_markdown(chunks) == "A word *stressed*"


def test_the_size_of_a_line_is_the_size_most_of_it_is_set_in() -> None:
    """A stray run promoted a line of body text to a heading.

    Lines commonly carry a separator left at whatever size the previous line
    used, so the largest size on a line is not what the line is set in.
    """
    chunks = down(
        [
            [
                run("A line of ordinary body text"),
                run(" •", x=210.0, size=HEADING),
            ],
            [run("with a second line under it.")],
        ]
    )

    assert as_markdown(chunks).startswith("A line of ordinary body text")
    assert "#" not in as_markdown(chunks)


def test_a_gutter_between_two_columns_comes_back_as_a_space() -> None:
    """Joined literally, a payslip reads "Employee nameReference"."""
    chunks = [run("Employee name"), run("Reference", x=400.0)]

    assert as_markdown(chunks) == "Employee name Reference"


def test_the_runs_of_one_word_are_not_pushed_apart() -> None:
    """A word split across runs sits about a glyph on, not a gutter on."""
    chunks = [run("Post"), run("Script", x=72.0 + len("Post") * BODY * 0.5)]

    assert as_markdown(chunks) == "PostScript"


def test_a_run_that_never_moved_the_matrix_continues_the_one_before_it() -> None:
    """Taken literally it sorts to the foot of the page and takes its words."""
    chunks = [
        run("The line as drawn"),
        Chunk(" and its tail.", 0.0, 0.0, BODY, False, False),
        run("A later line.", y=TOP - LINE_HEIGHT),
    ]

    assert as_markdown(chunks) == "The line as drawn and its tail. A later line."


def test_the_padding_the_extractor_used_is_not_kept() -> None:
    """A run arrives carrying the newlines and spaces that held the page shape."""
    chunks = [run("   Indented\n   forty spaces in   ")]

    assert as_markdown(chunks) == "Indented forty spaces in"


def test_a_page_that_drew_nothing_is_nothing() -> None:
    assert as_markdown([]) == ""
    assert as_markdown([run("   ")]) == ""


def test_lines_are_returned_top_of_the_page_first() -> None:
    """A PDF counts y up from the foot, so the largest y is the first line."""
    chunks = [run("Second", y=TOP - LINE_HEIGHT), run("First", y=TOP)]

    assert [line.text for line in lines_of(chunks)] == ["First", "Second"]


def test_chunks_within_a_few_points_of_each_other_are_one_line() -> None:
    """A run set slightly off the baseline is still on the line it reads on."""
    chunks = [run("Level"), run(" with it", x=110.0, y=TOP - 1.5)]

    assert len(lines_of(chunks)) == 1


def test_the_body_size_is_weighted_by_how_much_text_is_set_in_it() -> None:
    """A page of headings over one long paragraph still reads the paragraph."""
    chunks = down(
        [
            [run("A", size=HEADING)],
            [run("B", size=HEADING)],
            [run("C", size=HEADING)],
            [run("A paragraph carrying most of the writing on this page.")],
        ]
    )

    assert body_size_of(lines_of(chunks)) == BODY


def test_a_page_with_no_text_at_all_has_no_body_size() -> None:
    assert body_size_of([]) == 0
