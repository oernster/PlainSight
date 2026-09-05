"""Turns a document's body into HTML for a reading surface.

One renderer rather than one per kind: what changes between kinds is a few
lines, while a reader that had to be handed the right renderer would be a
reader that could be handed the wrong one.

The Markdown extensions are the ones the documents actually use: fenced code,
tables and the sane list handling that keeps a nested list nested.
"""

from __future__ import annotations

from html import escape

import markdown

from ..domain.document import DocumentKind

EXTENSIONS = ("fenced_code", "tables", "sane_lists")


class DocumentHtmlRenderer:
    """Rendering through the markdown package; verbatim where that is right."""

    def render(self, body: str, kind: DocumentKind) -> str:
        """The body as HTML, laid out as this kind of document asks.

        A kind that does not reflow is shown exactly as it was typed, inside a
        preformatted block with its own characters escaped. Passing plain text
        through a Markdown renderer would silently rewrite it: a line of
        hyphens becomes a heading rule, a leading asterisk becomes a bullet and
        the author's own line breaks disappear.
        """
        if kind.reflows:
            return markdown.markdown(body, extensions=list(EXTENSIONS))
        return f"<pre>{escape(body)}</pre>"
