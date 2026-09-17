"""How much there is of a document: its characters and its lines.

Counted over the text the document holds, before anything is done to present
it. Softening a long passage inserts breaks for the eye and a renderer wraps
the result to the column; neither changes the document, so neither may change
what is counted.

It is the text being read rather than the bytes of the file: a Markdown
document that declares a frontmatter block is counted beneath it, since those
fields are shown as a header rather than read as part of the document. A PDF
or a Word file has no file text to count at all.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Extent:
    """The size of a document's text, said the two ways a reader asks it.

    ``characters`` counts every character of the text, line endings included.
    ``lines`` counts the lines the text is written on: a final line ending
    closes the line before it rather than opening another, so a file of three
    lines reads as three whether or not it ends with a break.
    """

    characters: int
    lines: int

    @classmethod
    def of(cls, text: str) -> Extent:
        """The extent of this text."""
        return cls(characters=len(text), lines=len(text.splitlines()))
