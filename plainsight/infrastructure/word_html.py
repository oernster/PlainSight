"""Builds the HTML a Word document becomes, knowing nothing about Word.

HTML rather than Markdown, which is what this reader used to hand over. The
difference is not a matter of taste. Markdown is a NARROWER language than the
document it is being asked to carry; it is an ambiguous one: text that
means nothing in Word is syntax in Markdown. An indent typed as four spaces
became a block of code; a paragraph opening with a hyphen would become a list
item, one opening with a hash a heading, a stray asterisk a mark of emphasis.
Each of those is one instance of a class with no end to it; patching the
instances one at a time is not a fix.

Escaping into HTML has an end to it. Five characters mean something and every
one of them has a named escape, so text that is escaped cannot be read as
markup, whatever the author typed. That is the whole reason for the change:
not that HTML is richer; it is that turning text into it is total.

Nothing here knows what a docx is. It is given pieces of text with their
emphasis and it returns HTML, which is what makes it testable without a file.
"""

from __future__ import annotations

from dataclasses import dataclass
from html import escape

from ..domain.passage import passages

BULLETED = "bulleted"
NUMBERED = "numbered"
STANDALONE = "standalone"

LISTS = {BULLETED: "ul", NUMBERED: "ol"}
DEEPEST_HEADING = 6
NO_HEADING = 0
FIRST = 0


@dataclass(frozen=True, slots=True)
class Piece:
    """A stretch of a paragraph set in one face."""

    text: str
    bold: bool = False
    italic: bool = False


@dataclass(frozen=True, slots=True)
class Block:
    """One piece of HTML, with what it needs from its neighbours.

    A list item cannot be written on its own: consecutive items belong inside
    one list element, which is a fact about the item after it rather than
    about the item itself. So each block says what it is and the assembling
    puts the wrappers on.
    """

    kind: str
    html: str


def paragraph(pieces: tuple[Piece, ...], heading: int, item: str) -> list[Block]:
    """One Word paragraph as one or more blocks of HTML.

    More than one where the paragraph is a wall. The passages are found in the
    text the author wrote, before a single character has been escaped or a tag
    put anywhere near it: a break placed in the finished HTML could land
    inside a tag or halfway through an escape, turning `&amp;` into two pieces
    of rubbish. Found first and rendered afterwards, a break can only ever
    fall between two whole characters of the original.

    A heading or a list item is never cut, however long it runs. Both are one
    thing by definition; a heading broken in two is two headings.
    """
    if not any(piece.text.strip() for piece in pieces):
        return []
    if heading > NO_HEADING:
        depth = min(heading, DEEPEST_HEADING)
        return [Block(STANDALONE, f"<h{depth}>{_inline(pieces)}</h{depth}>")]
    if item:
        return [Block(item, f"<li>{_inline(pieces)}</li>")]
    return [
        Block(STANDALONE, f"<p>{_inline(rested)}</p>") for rested in _rested(pieces)
    ]


def plain(text: str) -> list[Block]:
    """A stretch of text with no emphasis in it, as paragraphs."""
    return paragraph((Piece(text),), NO_HEADING, "")


def table(rows: list[list[str]]) -> Block:
    """A table of data, as the table it is.

    The first row is the heading row, which is what Word's own tables mean by
    it and what a reader takes from the top row of any table they are shown.
    """
    head, *rest = rows
    width = max(len(row) for row in rows)
    lines = ["<table>", _row(head, width, "th")]
    lines.extend(_row(row, width, "td") for row in rest)
    lines.append("</table>")
    return Block(STANDALONE, "".join(lines))


def assembled(blocks: list[Block]) -> str:
    """Every block in order, with a list element around each run of items."""
    out: list[str] = []
    open_list = ""
    for block in blocks:
        if block.kind != open_list:
            if open_list:
                out.append(f"</{LISTS[open_list]}>")
            open_list = block.kind if block.kind in LISTS else ""
            if open_list:
                out.append(f"<{LISTS[open_list]}>")
        out.append(block.html)
    if open_list:
        out.append(f"</{LISTS[open_list]}>")
    return "\n".join(out)


def _row(cells: list[str], width: int, tag: str) -> str:
    """One table row, padded to the width of the widest row in the table."""
    padded = list(cells) + [""] * (width - len(cells))
    return (
        "<tr>"
        + "".join(f"<{tag}>{escape(_flat(cell))}</{tag}>" for cell in padded)
        + "</tr>"
    )


def _flat(text: str) -> str:
    """A cell's text on one line, which is all a table row has room for."""
    return " ".join(text.split())


def _inline(pieces: tuple[Piece, ...]) -> str:
    """The pieces as HTML, each escaped and wearing the marks of its face."""
    return "".join(_marked(piece) for piece in pieces)


def _marked(piece: Piece) -> str:
    """One piece, escaped, inside whatever elements its face asks for.

    A piece holding nothing but space is left bare. Emphasis on a space shows
    as nothing and says nothing; the space itself is what matters there.
    """
    text = escape(piece.text)
    if not piece.text.strip():
        return text
    if piece.italic:
        text = f"<em>{text}</em>"
    if piece.bold:
        text = f"<strong>{text}</strong>"
    return text


def _rested(pieces: tuple[Piece, ...]) -> list[tuple[Piece, ...]]:
    """The pieces regrouped into passages, cut where a reader needs a rest."""
    whole = "".join(piece.text for piece in pieces)
    groups = passages(whole)
    if len(groups) == 1:
        return [pieces]
    remaining = list(pieces)
    return [_taken(remaining, len(group)) for group in groups]


def _taken(remaining: list[Piece], wanted: int) -> tuple[Piece, ...]:
    """The next so many characters, splitting a piece where one straddles.

    The list is consumed as it goes, so the caller walking the passages in
    order gets each one exactly once. A piece cut in half keeps its face on
    both sides of the cut, since the cut is the reader's rather than the
    author's.
    """
    taken: list[Piece] = []
    while wanted > 0 and remaining:
        piece = remaining[FIRST]
        if len(piece.text) <= wanted:
            taken.append(piece)
            wanted -= len(piece.text)
            remaining.pop(FIRST)
            continue
        taken.append(Piece(piece.text[:wanted], piece.bold, piece.italic))
        remaining[FIRST] = Piece(piece.text[wanted:], piece.bold, piece.italic)
        wanted = 0
    return tuple(taken)
