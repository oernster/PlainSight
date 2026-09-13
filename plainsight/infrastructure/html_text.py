"""Whether a page shows any text once its scripts, styles and markup are gone.

A page is empty when the reading surface would show no text for it. That was
measured against a Qt text document rather than assumed: it shows nothing held
in a script, a style, a title or the head; nothing in a comment; nothing for a
lone non-breaking space. It does show what a ``noscript`` or a ``template``
holds, since nothing here runs either of them.

The standard library's own parser does the reading. It never raises on markup
it does not understand, so a page somebody wrote badly is still judged.
"""

from __future__ import annotations

from html.parser import HTMLParser

UNSHOWN_ELEMENTS = frozenset({"script", "style", "title", "head"})
BODY_ELEMENT = "body"


class _TextFinder(HTMLParser):
    """Watches for text that sits outside every element the surface hides."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._hidden_depth = 0
        self.found = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        # A body opens after the head whether or not the head was closed, so
        # an unclosed head cannot hide the whole page.
        if tag == BODY_ELEMENT:
            self._hidden_depth = 0
        elif tag in UNSHOWN_ELEMENTS:
            self._hidden_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in UNSHOWN_ELEMENTS and self._hidden_depth:
            self._hidden_depth -= 1

    def handle_data(self, data: str) -> None:
        if not self._hidden_depth and data.strip():
            self.found = True


def shows_text(markup: str) -> bool:
    """Whether this page puts any text in front of a reader."""
    finder = _TextFinder()
    finder.feed(markup)
    finder.close()
    return finder.found
