"""The reading pane: one document, rendered, reading itself down the page.

It is a stop on the ring only while it overflows. A page that fits scrolls
nowhere, so focusing it would let the user do nothing.
"""

from __future__ import annotations

from dataclasses import dataclass
from html import escape

from PySide6.QtCore import QPoint, QTimer
from PySide6.QtGui import QTextDocument
from PySide6.QtWidgets import QWidget

from ..application.ports import DocumentRenderer
from ..domain.document import Document
from ..domain.passage import soften
from .reading_pane import ReadingPane
from .theme import Palette, document_style

EMPTY_MESSAGE = (
    "<h2>No documents here</h2>"
    "<p>Nothing beneath this folder is a Markdown or text file. "
    "Use the folder button to browse somewhere else.</p>"
)
NOTHING_SELECTED = "<h2>Select a document</h2><p>Pick one from the list to read it.</p>"

AT_THE_TOP = 0
NO_OVERFLOW = 0
VIEWPORT_LEFT = 0
VIEWPORT_TOP = 0
NOT_MEASURED = -1
# How long to keep watching for the page to come back to the height it had.
# A change of colour alters no text, so the height returns and the exact place
# with it; a change of size keeps its new height and the watch simply expires.
SETTLES_WITHIN_MS = 1500


@dataclass(frozen=True, slots=True)
class Place:
    """Where a reader had reached, said in both of the ways that can be used.

    The pixel is exact while the page keeps its height, which a change of
    colour does. The character survives a change of size, which the pixel does
    not, since the same fraction of a reflowed page is different words.
    """

    pixel: int
    height: int
    character: int


class DocumentView(ReadingPane):
    """A rendered document, on the shared reading region."""

    def __init__(
        self,
        renderer: DocumentRenderer,
        palette: Palette,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setOpenExternalLinks(True)
        self.document().setDefaultStyleSheet(document_style(palette))
        self._renderer = renderer
        self._palette = palette
        self._showing: Document | None = None
        self._place: Place | None = None
        # The document is held here as well as handed to the widget: Qt does
        # not take ownership of one it is given, so a document kept only by the
        # widget is collected out from under it.
        self._document: QTextDocument | None = None
        self._measured_at = NOT_MEASURED
        self._exact: Place | None = None
        self._watching = False
        self._give_up = QTimer(self)
        self._give_up.setSingleShot(True)
        self._give_up.setInterval(SETTLES_WITHIN_MS)
        self._give_up.timeout.connect(self._stop_watching)
        self.show_nothing()

    def wear(self, palette: Palette) -> None:
        """Take the colours of this palette; the caller re-renders after.

        Forgetting what is shown is what makes that re-render happen: a
        document only takes a style sheet as it is parsed, so the same document
        must genuinely be drawn again for a change of colour to reach it.
        """
        self._palette = palette
        self._showing = None

    def remember_place(self) -> None:
        """Take note of where the reader is, before anything moves them.

        Before the stylesheet changes rather than after. Read afterwards, it
        was measured capturing the wrong words: a new text size has already
        reflowed the page by then, so what it records is where the reader was
        thrown to rather than where they were.
        """
        bar = self.verticalScrollBar()
        if bar.maximum() == NO_OVERFLOW or bar.value() == AT_THE_TOP:
            self._place = None
            return
        cursor = self.cursorForPosition(QPoint(VIEWPORT_LEFT, VIEWPORT_TOP))
        self._place = Place(
            pixel=bar.value(), height=bar.maximum(), character=cursor.position()
        )

    def _return_to(self, place: Place) -> None:
        """Put the reader back on the page that has just replaced theirs.

        The page is laid out before it is ever attached, so the scrollbar has
        its full range the moment this runs. There is nothing to wait for and
        no moment at which the position could be lost, which is the point: the
        earlier attempts all tried to restore a position after it had already
        been thrown away.

        A page of unchanged height is the same words in new colours, so the
        pixel is exact. A page of changed height has reflowed under a new text
        size, where the same pixel would be different words, so the character
        is followed instead.
        """
        bar = self.verticalScrollBar()
        if bar.maximum() == place.height:
            bar.setValue(place.pixel)
            return
        cursor = self.textCursor()
        cursor.setPosition(min(place.character, self.document().characterCount() - 1))
        self.setTextCursor(cursor)
        bar.setValue(bar.value() + self.cursorRect(cursor).top())
        # The words are the best that can be done while the page is a different
        # height. It rarely stays one: a change of colour alters no text, so the
        # height settles back to what it was within a moment; the pixel that
        # was taken then is exact again. Measured going 33783 to 43742 to 36386
        # and back to 33783, with the reader left ten pixels adrift for want of
        # waiting. So the height is watched, then the exact place applied the
        # moment it returns.
        self._exact = place
        self._watch_for_the_height_to_return()

    def _watch_for_the_height_to_return(self) -> None:
        """Listen until the page is the size it was; give up after a while."""
        if self._watching:
            return
        self._watching = True
        self.verticalScrollBar().rangeChanged.connect(self._height_changed)
        self._give_up.start()

    def _stop_watching(self) -> None:
        """Stop listening. A page that kept its new height reflowed for real."""
        if not self._watching:
            return
        self._watching = False
        self._exact = None
        self._give_up.stop()
        self.verticalScrollBar().rangeChanged.disconnect(self._height_changed)

    def _height_changed(self, _lowest: int, highest: int) -> None:
        """The page has been resized; put the reader back exactly if it fits."""
        place = self._exact
        if place is None or highest != place.height:
            return
        self.verticalScrollBar().setValue(place.pixel)
        self._stop_watching()

    def show_nothing(self) -> None:
        """The state before a document has been picked."""
        self._showing = None
        self._set(NOTHING_SELECTED)

    def show_empty_root(self) -> None:
        """The state when the chosen folder holds no documents."""
        self._showing = None
        self._set(EMPTY_MESSAGE)

    def show_document(self, document: Document) -> None:
        """Render one document: header, then body or failure, then any long field.

        A document already on screen and unchanged is left exactly as it is, half
        read and at the place the reader had reached. The library is re-read
        every time the window is activated; each re-read used to redraw and send
        the page back to the top, so leaving to look something up and
        coming back lost your place; scrolling looked as though it had simply
        been ignored. A document compares by value, so a document edited on disk
        is a different document and is drawn again as it should be.
        """
        if document == self._showing:
            return
        self._showing = document
        self._set(_header(document) + self._body(document) + _long_fields(document))

    def _body(self, document: Document) -> str:
        """The document, given somewhere for the eye to rest on the way down.

        The softening happens here rather than anywhere nearer the file: it is
        a decision about presenting the text; the text on disk is never touched
        by it. A kind that does not reflow is not softened at all, since its
        line breaks are the author's own layout rather than the renderer's.
        """
        if not document.is_readable:
            return f"<p><b>{escape(document.failure)}</b></p>"
        body = soften(document.body) if document.kind.reflows else document.body
        return self._renderer.render(body, document.kind)

    def _set(self, html: str) -> None:
        """Show this content, at the start unless a place was kept for it.

        The document is built and laid out here rather than handed to the
        widget as text. Setting text on the live widget empties its scroll
        position before the replacement has a shape, so the position has to be
        put back afterwards; that is the race every earlier attempt at this
        lost. A document that arrives already laid out never creates the gap.
        """
        place = self._place
        self._place = None

        # Only when the font has moved. The column is a count of characters and
        # so a fact about the font; re-measuring it on every redraw reflows
        # the page for a change of colour too, which was measured shifting the
        # height by six hundred pixels and pushing an exact restore onto the
        # approximate path for no reason.
        wanted = self.readable_width()
        if wanted != self._measured_at:
            self._measured_at = wanted
            self.apply_measure()

        previous = self.document()
        width = previous.textWidth() if previous is not None else NOT_MEASURED
        if width <= NO_OVERFLOW:
            width = self.viewport().width()

        document = QTextDocument(self)
        # Before the text, because the font decides how the text lays out.
        # A document built rather than taken from the widget starts on the
        # APPLICATION default font, not the one the stylesheet just gave this
        # pane; setDocument does not put that right afterwards. Measured at
        # 9pt in all three settings while the widget went 14, 17 and 20: the
        # column re-measured and the page re-centred while the words being read
        # never changed size at all.
        document.setDefaultFont(self.font())
        document.setDefaultStyleSheet(document_style(self._palette))
        document.setHtml(html)
        # Laid out at the width the widget itself was using, not at the raw
        # viewport width. Those differ; the difference was measured moving
        # the page height by six hundred pixels on a change of colour alone,
        # which turned an exact restore into an approximate one for nothing.
        document.setTextWidth(width)
        self._document = document
        self.setDocument(document)

        if place is None:
            self.scroller.restart()
        else:
            self._return_to(place)
            # Hold still for a moment before reading on. The page has just
            # changed shape under the reader; carrying on scrolling through
            # that gives them a moving target while it settles; the same pause
            # a hand on the wheel earns.
            self.scroller.suspend()
        self.sync_focus_policy()


def _header(document: Document) -> str:
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


def _long_fields(document: Document) -> str:
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
