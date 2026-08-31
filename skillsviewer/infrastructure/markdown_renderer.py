"""Turns a skill's body into HTML for a reading surface.

The extensions are the ones the skills actually use: fenced code, tables and
the sane list handling that keeps a nested list nested.
"""

from __future__ import annotations

import markdown

EXTENSIONS = ("fenced_code", "tables", "sane_lists")


class PythonMarkdownRenderer:
    """Rendering through the markdown package."""

    def render(self, body: str) -> str:
        """The body as HTML."""
        return markdown.markdown(body, extensions=list(EXTENSIONS))
