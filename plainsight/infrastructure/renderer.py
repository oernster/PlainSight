"""Turns a document's body into HTML for a reading surface.

One renderer rather than one per kind: what changes between kinds is a few
lines, while a reader that had to be handed the right renderer would be a
reader that could be handed the wrong one.

The Markdown extensions are the ones the documents actually use: fenced code,
tables and the sane list handling that keeps a nested list nested.
"""

from __future__ import annotations

import re
from html import escape

import markdown

from ..domain.document import CODE_BLOCK_CLASS, DocumentKind, Presentation

EXTENSIONS = ("fenced_code", "tables", "sane_lists")
# A preformatted block never nests another and its text arrives escaped, so the
# first closing tag after an opening one is always its own.
PREFORMATTED = re.compile(r"<pre>.*?</pre>", re.DOTALL)
CODE_BLOCK_OPEN = (
    f'<table class="{CODE_BLOCK_CLASS}" width="100%" cellspacing="0"><tr><td>'
)
CODE_BLOCK_CLOSE = "</td></tr></table>"


class DocumentHtmlRenderer:
    """Rendering through the markdown package; verbatim where that is right."""

    def render(self, body: str, kind: DocumentKind) -> str:
        """The body as HTML, laid out as this kind of document asks.

        Text kept as typed is shown exactly as it was, inside a preformatted
        block with its own characters escaped. Passing plain text through a
        Markdown renderer would silently rewrite it: a line of hyphens becomes
        a heading rule, a leading asterisk becomes a bullet and the author's
        own line breaks disappear.

        HTML is handed over untouched, because it is already what this method
        exists to produce. Rewriting it would mean parsing a document only to
        write the same document back out, with every pass losing whatever the
        parser did not understand.
        """
        presentation = kind.presentation
        if presentation is Presentation.LAID_OUT:
            html = markdown.markdown(body, extensions=list(EXTENSIONS))
            return PREFORMATTED.sub(lambda block: _boxed(block.group()), html)
        if presentation is Presentation.ALREADY_HTML:
            return body
        return _boxed(f"<pre>{escape(body)}</pre>")


def _boxed(block: str) -> str:
    """A preformatted block inside a table of one cell.

    Qt paints a preformatted block's background line by line, each only as far
    as that line reaches. A block wider than the column, a diagram being the
    measured case, came out as a ragged staircase of dark strips cut off at the
    column's edge. A single cell is one rectangle as wide as its widest line,
    which scrolls sideways as a whole.
    """
    return CODE_BLOCK_OPEN + block + CODE_BLOCK_CLOSE
