"""What a document says about itself, around the text it was opened for.

The title and the short fields head the page; any field too long for a header
row follows the body under a heading of its own.
"""

from __future__ import annotations

from html import escape

from ..domain.document import Document


def header(document: Document) -> str:
    """The title, the description and whatever else the document declares.

    The title is the declared name where there is one and the file name
    otherwise, so a document that calls itself something opens under that
    name while still listing in the tree as the file it is.
    """
    parts = [f"<h1>{escape(document.title)}</h1>"]
    if document.description:
        parts.append(f"<p><i>{escape(document.description)}</i></p>")
    fields = _fields(document)
    if fields:
        parts.append(fields)
    parts.append("<hr>")
    return "".join(parts)


def _fields(document: Document) -> str:
    """The short frontmatter this document declares, beyond the two already shown."""
    rows = [
        f"<li><b>{escape(key)}</b>: {escape(value)}</li>"
        for key, value in document.header_fields
    ]
    return "" if not rows else "<ul>" + "".join(rows) + "</ul>"


def long_fields(document: Document) -> str:
    """Every oversized frontmatter value, each under a heading of its own.

    These follow the body rather than heading it, so the text a reader opened
    the document for is the first thing they meet.
    """
    if not document.long_fields:
        return ""
    sections = "".join(
        f"<h2>{escape(key)}</h2><p>{escape(value)}</p>"
        for key, value in document.long_fields
    )
    return "<hr>" + sections
