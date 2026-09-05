"""Rebuilds a PDF page as a document rather than as the words that were on it.

A PDF says nothing about what its text MEANS. There is no heading in the file,
no paragraph and no list; there are glyphs, each with a place, a size and a
face. Everything a reader sees in a PDF viewer, they see because a person laid
it out and their eye reads the layout back.

So that is what is read back here. A line larger than the body is a heading and
how much larger settles its depth. A line in the bold face is emphasised. A line
opening with a bullet is an item. Consecutive lines of body text are one
paragraph, since a line break inside a PDF paragraph is a fact about the page
width rather than about the writing. A wider gap than usual between lines is
where one block ends and the next begins.

Read the words alone and a CV arrives as a wall of monospace with its headings,
its emphasis and its lists all gone; read where they sat and it arrives as a
document. Neither is what the file says, because the file does not say. This is
the reading that puts back what the author's eye was meant to pick up.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from itertools import pairwise

BOLD = "**"
ITALIC = "*"
BULLET = "- "
HEADING_PREFIX = "#"
DEEPEST_HEADING = 3
# A line has to stand out from the body by this much to be a heading rather
# than a body line that happens to carry a slightly larger glyph.
HEADING_RATIO = 1.08
# Lines further apart than their usual spacing by this much start a new block.
# Measured on a real CV: lines within a paragraph sat 11.2 points apart and the
# space between paragraphs was 14.3, against a usual spacing of 10.6. A wider
# margin than this read the whole of a section as one paragraph.
BLOCK_GAP_RATIO = 1.25
# Two chunks on the same line are within this many points of one another.
SAME_LINE_POINTS = 3.0
# A run starting further along the line than this many ems per character of the
# run before it did not continue that run. No proportional face draws a glyph a
# whole em wide, so a whole em each is already past anything text can account
# for. Measured over a real CV's 169 joins that carry no space of their own:
# every continuing run sat between 0.29 and 0.58 ems per character and every
# jump across the page sat at 2.0 or beyond, with nothing in between.
WIDEST_ADVANCE_EMS = 1.0
# More of a page than this being headings means the page has none.
MOST_OF_A_PAGE = 0.35
# The glyphs a page draws to open an item. Every one of them is a real
# character on the page: a bullet the word processor made out of a tab and a
# letter cannot appear here, since a line is tidied before it is read and the
# tab is a space by then.
BULLET_GLYPHS = ("•", "●", "▪", "‣", "·")
NOTHING = 0
FIRST = 0


@dataclass(frozen=True, slots=True)
class Chunk:
    """One run of text the page drew, with where it sat and how it looked."""

    text: str
    x: float
    y: float
    size: float
    bold: bool
    italic: bool


@dataclass(frozen=True, slots=True)
class Line:
    """Every chunk that sat on one line of the page, in reading order."""

    chunks: tuple[Chunk, ...]

    @property
    def y(self) -> float:
        return self.chunks[FIRST].y

    @property
    def size(self) -> float:
        """The size most of this line's text is set in.

        Most of it rather than the largest on it: a line commonly carries a
        stray run, a space or a separator, left at whatever size the previous
        one used. Taking the largest let one such run promote a line of body
        text to a heading, which is how the tail of a paragraph came to be
        rendered as one.
        """
        weight: Counter[float] = Counter()
        for chunk in self.chunks:
            weight[round(chunk.size, 1)] += len(chunk.text.strip())
        if not weight:
            return self.chunks[FIRST].size
        return weight.most_common(1)[FIRST][FIRST]

    @property
    def spaced(self) -> tuple[Chunk, ...]:
        """The chunks with a space put back wherever the page left a gap."""
        return _separated(self.chunks)

    @property
    def text(self) -> str:
        return _tidy("".join(chunk.text for chunk in self.spaced))

    @property
    def all_bold(self) -> bool:
        return all(chunk.bold for chunk in self.chunks if chunk.text.strip())


def _tidy(text: str) -> str:
    """One space wherever the page left whitespace; none at the ends.

    A run of text arrives carrying the newlines and the padding the extractor
    used to hold the page's shape. Rebuilding the page as a document is exactly
    the decision not to keep that shape, so it goes here rather than reaching
    the reader as a paragraph that starts forty spaces in.
    """
    return " ".join(text.split())


def _apart(before: Chunk, after: Chunk) -> bool:
    """Whether this run starts afresh on the line rather than continuing the last.

    Two things drawn side by side on one line arrive as two runs with nothing
    between them, so joined literally a payslip reads "Employee nameReference".
    The runs of a single word arrive exactly the same way, which is why the two
    are told apart by distance rather than by anything in the text: a run that
    continues the one before it begins about a glyph further along, whereas a
    second column begins the width of the page's gutter further along.
    """
    span = len(before.text) * before.size
    if span <= NOTHING:
        return False
    return (after.x - before.x) > span * WIDEST_ADVANCE_EMS


def _separated(chunks: tuple[Chunk, ...]) -> tuple[Chunk, ...]:
    """The chunks with a space put back wherever the page left a gap.

    Only where neither run carries a space of its own at the join. A page that
    already spaced its columns needs nothing doing to it; measured, a real
    payslip is entirely of that sort.
    """
    out: list[Chunk] = []
    for chunk in chunks:
        if out and _wants_space(out[-1], chunk):
            chunk = Chunk(
                f" {chunk.text}",
                chunk.x,
                chunk.y,
                chunk.size,
                chunk.bold,
                chunk.italic,
            )
        out.append(chunk)
    return tuple(out)


def _wants_space(before: Chunk, after: Chunk) -> bool:
    """Whether a space belongs between these two runs and is not there already."""
    if before.text[-1:].isspace() or after.text[:1].isspace():
        return False
    return _apart(before, after)


def lines_of(chunks: list[Chunk]) -> list[Line]:
    """The chunks gathered into the lines they sat on, top of the page first.

    A chunk carrying no position of its own continues the one before it: the
    extractor reports a run that never moved the text matrix at the origin, so
    taken literally it would sort to the foot of the page and take its words
    with it.
    """
    placed: list[Chunk] = []
    for chunk in chunks:
        if not chunk.text:
            continue
        if chunk.x == NOTHING and chunk.y == NOTHING and placed:
            last = placed[-1]
            placed.append(
                Chunk(chunk.text, last.x, last.y, chunk.size, chunk.bold, chunk.italic)
            )
            continue
        placed.append(chunk)

    rows: list[list[Chunk]] = []
    for chunk in sorted(placed, key=lambda one: (-one.y, one.x)):
        if rows and abs(rows[-1][FIRST].y - chunk.y) <= SAME_LINE_POINTS:
            rows[-1].append(chunk)
            continue
        rows.append([chunk])
    return [Line(tuple(row)) for row in rows if "".join(c.text for c in row).strip()]


def body_size_of(lines: list[Line]) -> float:
    """The size most of the writing is set in, which everything else is read against.

    Weighted by how much text is set in it rather than by how many lines carry
    it, so a page of headings over one long paragraph still reads the paragraph
    as the body.
    """
    weight: Counter[float] = Counter()
    for line in lines:
        for chunk in line.chunks:
            weight[round(chunk.size, 1)] += len(chunk.text.strip())
    if not weight:
        return NOTHING
    return weight.most_common(1)[FIRST][FIRST]


def as_markdown(chunks: list[Chunk]) -> str:
    """One page of chunks, as the document a reader was meant to see."""
    lines = lines_of(chunks)
    if not lines:
        return ""
    body = body_size_of(lines)
    depths = _heading_depths(lines, body)
    gap = _usual_gap(lines)

    blocks: list[str] = []
    open_block: list[str] = []
    in_list = False

    def close() -> None:
        nonlocal in_list
        if open_block:
            blocks.append(" ".join(open_block))
            open_block.clear()
        in_list = False

    previous: Line | None = None
    for line in lines:
        far = previous is not None and (previous.y - line.y) > gap * BLOCK_GAP_RATIO
        depth = depths.get(round(line.size, 1))
        item = _bullet_of(line.text)
        if depth is not None:
            close()
            blocks.append(f"{HEADING_PREFIX * depth} {line.text}")
        elif item is not None:
            close()
            in_list = True
            open_block.append(f"{BULLET}{_emphasised(line, body, skip=item)}")
        else:
            # A line under an item and close to it is the rest of that item.
            # An item wraps like any other text, so its second line arrives
            # carrying no bullet; started as a paragraph of its own it broke
            # every wrapped item on the page in two.
            if far:
                close()
            open_block.append(_emphasised(line, body))
        previous = line
    close()
    return "\n\n".join(block for block in blocks if block.strip())


def _heading_depths(lines: list[Line], body: float) -> dict[float, int]:
    """Which sizes are headings and how deep each one is.

    Depth follows size: the largest is the top of the page and each smaller
    heading size sits under it, which is the ordering a reader takes from the
    page without being told.

    A page where most lines would be headings has no headings to find, so none
    are taken. That is what a form or a payslip looks like from here: its text
    is set in a spread of sizes with no one body among them; read without this
    guard a whole payslip came back as a stack of headings, every line of it
    shouting.
    """
    bigger = [line for line in lines if line.size > body * HEADING_RATIO]
    if len(bigger) > len(lines) * MOST_OF_A_PAGE:
        return {}
    ordered = sorted({round(line.size, 1) for line in bigger}, reverse=True)
    return {
        size: min(depth, DEEPEST_HEADING) for depth, size in enumerate(ordered, start=1)
    }


def _usual_gap(lines: list[Line]) -> float:
    """How far apart consecutive lines normally sit on this page."""
    gaps = [
        round(before.y - after.y, 1)
        for before, after in pairwise(lines)
        if before.y > after.y
    ]
    if not gaps:
        return float("inf")
    return Counter(gaps).most_common(1)[FIRST][FIRST]


def _bullet_of(text: str) -> str | None:
    """The bullet this line opens with, where it opens with one."""
    stripped = text.lstrip()
    for glyph in BULLET_GLYPHS:
        if stripped.startswith(glyph):
            return glyph
    return None


def _emphasised(line: Line, body: float, skip: str | None = None) -> str:
    """The line's text, carrying the emphasis its faces were setting.

    A line set wholly in the bold face at body size is one emphasis rather than
    several: a run of separately marked words reads as a stutter of asterisks
    where the author put a single strong line.
    """
    if line.all_bold and line.size <= body * HEADING_RATIO:
        text = line.text
        if skip:
            text = text[len(skip) :].lstrip()
        return f"{BOLD}{text}{BOLD}" if text else text
    return _marked(line, skip)


def _spaced(raw: str, tidied: str) -> str:
    """The tidied run, keeping whether there was a space at either end of it.

    Runs sit against one another, so a run that ended in a space and one that
    began with one both have a word boundary to preserve. Tidying each in
    isolation would run the last word of one into the first of the next.
    """
    if not tidied:
        return " " if raw else ""
    lead = " " if raw[:1].isspace() else ""
    trail = " " if raw[-1:].isspace() else ""
    return f"{lead}{tidied}{trail}"


def _marked(line: Line, skip: str | None) -> str:
    """The line rebuilt run by run, each run of a face marked once."""
    runs: list[tuple[bool, bool, str]] = []
    for chunk in line.spaced:
        face = (chunk.bold, chunk.italic)
        if runs and (runs[-1][0], runs[-1][1]) == face:
            runs[-1] = (face[0], face[1], runs[-1][2] + chunk.text)
            continue
        runs.append((face[0], face[1], chunk.text))

    out: list[str] = []
    for bold, italic, raw in runs:
        text = _tidy(raw)
        if not text or not (bold or italic):
            out.append(_spaced(raw, text))
            continue
        marks = f"{BOLD if bold else ''}{ITALIC if italic else ''}"
        out.append(_spaced(raw, f"{marks}{text}{marks}"))
    text = _tidy("".join(out))
    if skip:
        text = text[len(skip) :].lstrip()
    return text
