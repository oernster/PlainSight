"""Giving a wall of text somewhere for the eye to rest, without rewriting it.

Some skills are written as single paragraphs of several thousand characters.
Typography alone cannot rescue those: line spacing and a capped measure make a
slab a well set slab. What a reader needs is somewhere to pause.

So an over-long passage is shown in groups of whole sentences with a gap
between them. Nothing is added, removed or reordered: the break goes between
two sentences that were already adjacent, exactly as line wrapping goes between
two words that were already adjacent. The guarantee is mechanical rather than
promised; it is asserted as a test. Take the breaks back out and the original
text returns character for character.

Sentence ends alone are not enough. Some passages are inventories rather than
prose, a run of named entries divided by commas and semicolons; the longest
measured holds seventeen thousand characters with a single sentence end in it.
Those get a second pass at the boundaries the author did write: the end of a
bracketed entry, then a semicolon, which already separates two clauses that
each stand alone. That pass runs only on a group still oversized after the first, so
ordinary prose is never broken anywhere but between sentences.

A break is never placed inside fenced or indented code, a heading, a table, an
inline code span or a bracketed aside, since each of those means the full stop
in front of it is probably not the end of a sentence.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator

Finder = Callable[[str], Iterator[int]]

SOFT_BREAK = "<br><br>"
# Roughly six lines at the length the reading pane holds a line to. Shorter
# than this reads as a paragraph already and is left exactly alone.
WALL_CHARACTERS = 500
# Roughly three lines: long enough to be a thought, short enough to take in.
GROUP_CHARACTERS = 280
# Never strand a fragment at the end; below this the last group keeps it.
MIN_TAIL_CHARACTERS = 120

TERMINATORS = ".?!"
OPENERS = "(["
CLOSERS = ")]"
CODE_MARK = "`"
FENCES = ("```", "~~~")
VERBATIM_STARTS = ("#", "|", ">")
INDENTED_CODE = "    "
NOT_SENTENCE_ENDS = frozenset(
    {
        "e.g.",
        "i.e.",
        "etc.",
        "cf.",
        "vs.",
        "no.",
        "approx.",
        "dr.",
        "mr.",
        "mrs.",
        "ms.",
        "st.",
        "fig.",
    }
)
LIST_BULLETS = ("-", "*", "+")
EVEN = 2
ENTRY_END = ", "
CLAUSE_END = "; "


def soften(body: str) -> str:
    """The same text, with a resting place inside any passage that is a wall."""
    out: list[str] = []
    block: list[str] = []
    fenced = False
    for line in body.splitlines(keepends=True):
        stripped = line.strip()
        if stripped.startswith(FENCES):
            out.extend(_flush(block))
            block = []
            fenced = not fenced
            out.append(line)
        elif fenced or _is_verbatim(line) or not stripped:
            out.extend(_flush(block))
            block = []
            out.append(line)
        else:
            if block and _starts_an_item(stripped):
                out.extend(_flush(block))
                block = []
            block.append(line)
    out.extend(_flush(block))
    return "".join(out)


def _flush(block: list[str]) -> list[str]:
    """The gathered passage, softened where it is long enough to need it."""
    return [] if not block else [_soften_passage("".join(block))]


def _is_verbatim(line: str) -> bool:
    """Whether this line is structure rather than prose, so it is left alone."""
    return line.startswith(INDENTED_CODE) or line.lstrip().startswith(VERBATIM_STARTS)


def _starts_an_item(stripped: str) -> bool:
    """Whether this line begins a fresh list item rather than continuing one."""
    head = stripped.split(" ", 1)[0]
    if head in LIST_BULLETS:
        return True
    return head.endswith(".") and head[:-1].isdigit()


def passages(text: str) -> tuple[str, ...]:
    """One passage cut into the passages a reader can rest between.

    A single passage where it is already short enough to read. Nothing is
    added, removed or reordered, so joining the passages back together returns
    the text character for character; that is what makes this safe to do to
    somebody else's writing.

    Given out as the passages themselves rather than as one string with breaks
    in it, because what a caller does with them differs. The reading surface
    wants them run together with a gap between; a reader building HTML wants
    each one as a paragraph of its own.
    """
    if len(text) <= WALL_CHARACTERS:
        return (text,)
    groups: list[str] = []
    for group in _grouped(text, _sentence_ends):
        if len(group) > WALL_CHARACTERS:
            groups.extend(_grouped(group, _written_breaks))
        else:
            groups.append(group)
    return tuple(groups)


def _soften_passage(text: str) -> str:
    """Group whole sentences, then take a second look at anything still a slab."""
    return SOFT_BREAK.join(passages(text))


def _grouped(text: str, boundaries: Finder) -> list[str]:
    """Cut the text at the given boundaries, once a group is big enough."""
    pieces: list[str] = []
    start = 0
    for end in boundaries(text):
        long_enough = end - start >= GROUP_CHARACTERS
        leaves_a_tail = len(text) - end >= MIN_TAIL_CHARACTERS
        if long_enough and leaves_a_tail:
            pieces.append(text[start:end])
            start = end
    pieces.append(text[start:])
    return pieces


def _sentence_ends(text: str) -> Iterator[int]:
    """Every place a sentence demonstrably ends, at the top level of the text.

    The index yielded is the first character of the sentence that follows, so
    splitting there and rejoining with the break in between puts every original
    character back where it was.
    """
    depth = 0
    ticks = 0
    for position, character in enumerate(text):
        if character == CODE_MARK:
            ticks += 1
        elif character in OPENERS:
            depth += 1
        elif character in CLOSERS:
            depth = max(0, depth - 1)
        elif character in TERMINATORS and depth == 0 and ticks % EVEN == 0:
            following = _after_the_space(text, position)
            if following is not None and _opens_a_sentence(text, position, following):
                yield following


def _after_the_space(text: str, position: int) -> int | None:
    """Where the next sentence starts; None when no whitespace follows."""
    walker = position + 1
    if walker >= len(text) or not text[walker].isspace():
        return None
    while walker < len(text) and text[walker].isspace():
        walker += 1
    return None if walker >= len(text) else walker


def _opens_a_sentence(text: str, terminator: int, following: int) -> bool:
    """Whether what follows reads as a new sentence rather than a continuation."""
    if not (text[following].isupper() or text[following] in "*`_"):
        return False
    return _word_ending_at(text, terminator) not in NOT_SENTENCE_ENDS


def _word_ending_at(text: str, terminator: int) -> str:
    """The word the terminator closes, folded, for the abbreviation check."""
    start = terminator
    while start > 0 and not text[start - 1].isspace():
        start -= 1
    return text[start : terminator + 1].casefold()


def _written_breaks(text: str) -> Iterator[int]:
    """The divisions the author wrote inside a sentence: entries and clauses.

    A closing bracket followed by a comma ends one named entry in an inventory;
    a semicolon separates two clauses that each stand on their own. Neither cuts
    a phrase in half, which is why these are the only two used.
    """
    depth = 0
    ticks = 0
    for position, character in enumerate(text):
        if character == CODE_MARK:
            ticks += 1
            continue
        if ticks % EVEN != 0:
            continue
        if character in OPENERS:
            depth += 1
        elif character in CLOSERS:
            depth = max(0, depth - 1)
            if depth == 0 and text[position + 1 : position + 3] == ENTRY_END:
                yield position + 1 + len(ENTRY_END)
        elif depth == 0 and text[position : position + 2] == CLAUSE_END:
            yield position + len(CLAUSE_END)
