"""The reading pane: one skill, rendered, reading itself down the page.

It is a stop on the ring only while it overflows. A page that fits scrolls
nowhere, so focusing it would let the user do nothing.
"""

from __future__ import annotations

from html import escape

from PySide6.QtCore import QPoint, QTimer
from PySide6.QtWidgets import QWidget

from ..application.ports import MarkdownRenderer
from ..domain.passage import soften
from ..domain.skill import Skill
from .reading_pane import ReadingPane
from .theme import Palette, document_style

EMPTY_MESSAGE = (
    "<h2>No skills here</h2>"
    "<p>Nothing beneath this folder holds a SKILL.md. "
    "Use the folder button to browse somewhere else.</p>"
)
NOTHING_SELECTED = "<h2>Select a skill</h2><p>Pick one from the list to read it.</p>"

AT_THE_TOP = 0
NO_OVERFLOW = 0
VIEWPORT_LEFT = 0
VIEWPORT_TOP = 0
# The next turn of the event loop, by which time the page has finished laying
# itself out.
SETTLED_MS = 0


class SkillView(ReadingPane):
    """A rendered skill, on the shared reading region."""

    def __init__(
        self,
        renderer: MarkdownRenderer,
        palette: Palette,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setOpenExternalLinks(True)
        self.document().setDefaultStyleSheet(document_style(palette))
        self._renderer = renderer
        self._palette = palette
        self._showing: Skill | None = None
        self._resuming: int | None = None
        self._settling: int | None = None
        # Owned by this widget rather than a bare singleShot, so it cannot
        # outlive the pane and fire into a deleted one.
        self._settle = QTimer(self)
        self._settle.setSingleShot(True)
        self._settle.setInterval(SETTLED_MS)
        self._settle.timeout.connect(self._resume_when_settled)
        self.show_nothing()

    def wear(self, palette: Palette) -> None:
        """Take the colours of this palette; the caller re-renders after.

        Forgetting what is shown is what makes that re-render happen: a
        document keeps the colours it was rendered under, so this is one of the
        two occasions the same skill must genuinely be drawn again.

        The reader's place is carried across that redraw, from whatever
        ``remember_place`` took before the change began.
        """
        self._palette = palette
        self._showing = None
        self.document().setDefaultStyleSheet(document_style(palette))

    def remember_place(self) -> None:
        """Take note of where the reader is, before anything moves them.

        Called before the stylesheet changes rather than after. Reading it
        afterwards was measured capturing the wrong words: a new text size has
        already reflowed the page by then, so the place recorded is where the
        reader was thrown to, not where they were.
        """
        self._resuming = self._place()

    def _place(self) -> int | None:
        """The first character the reader can see, as an offset into the text.

        A character rather than a pixel, deliberately. The pixel answer was
        tried first and is wrong twice over: the document lays out again after
        the redraw, so the height read at the moment of restoring is stale; at
        another text size the same fraction of the page is different words
        anyway. An offset into the text survives both, because the words do not
        move relative to each other.
        """
        bar = self.verticalScrollBar()
        if bar.maximum() == NO_OVERFLOW or bar.value() == AT_THE_TOP:
            return None
        return self.cursorForPosition(QPoint(VIEWPORT_LEFT, VIEWPORT_TOP)).position()

    def _resume(self, position: int) -> None:
        """Bring the words the reader was on back to the top of the page."""
        cursor = self.textCursor()
        cursor.setPosition(min(position, self.document().characterCount() - 1))
        self.setTextCursor(cursor)
        bar = self.verticalScrollBar()
        bar.setValue(bar.value() + self.cursorRect(cursor).top())

    def show_nothing(self) -> None:
        """The state before a skill has been picked."""
        self._showing = None
        self._set(NOTHING_SELECTED)

    def show_empty_root(self) -> None:
        """The state when the chosen folder holds no skills."""
        self._showing = None
        self._set(EMPTY_MESSAGE)

    def show_skill(self, skill: Skill) -> None:
        """Render one skill: header, then body or failure, then any long field.

        A skill already on screen and unchanged is left exactly as it is, half
        read and at the place the reader had reached. The library is re-read
        every time the window is activated; each re-read used to redraw and send
        the page back to the top, so leaving to look something up and
        coming back lost your place; scrolling looked as though it had simply
        been ignored. A skill compares by value, so a document edited on disk
        is a different skill and is drawn again as it should be.
        """
        if skill == self._showing:
            return
        self._showing = skill
        self._set(_header(skill) + self._body(skill) + _long_fields(skill))

    def _body(self, skill: Skill) -> str:
        """The document, given somewhere for the eye to rest on the way down.

        The softening happens here rather than anywhere nearer the file: it is
        a decision about presenting the text; the text on disk is never touched
        by it.
        """
        if not skill.is_readable:
            return f"<p><b>{escape(skill.failure)}</b></p>"
        return self._renderer.render(soften(skill.body))

    def _set(self, html: str) -> None:
        """Show this content, at the start unless a place was kept for it.

        A genuinely new page returns the reading cycle to its start hold. The
        same page in new colours does not: restarting sets the bar to the top,
        which is the whole of the defect this guards against.
        """
        resuming = self._resuming
        self._resuming = None
        self.setHtml(html)
        if resuming is None:
            self.scroller.restart()
        else:
            # Twice, on purpose. A document that has finished laying out is put
            # back correctly by the first call. One that has not reports a zero
            # rect for a block it has not placed yet, and zero plus a bar that
            # setHtml has just reset is the top of the page, which is the whole
            # of the reported defect. The height of a fresh document was
            # measured still moving after this call returns, from 16560 to
            # 14687, so the second pass is the one that can be trusted.
            # Re-applying a place already reached moves nothing.
            self._resume(resuming)
            self._settling = resuming
            self._settle.start()
        self.sync_focus_policy()

    def _resume_when_settled(self) -> None:
        """The second pass, once the page has stopped changing shape."""
        position = self._settling
        self._settling = None
        if position is not None:
            self._resume(position)
        self.sync_focus_policy()


def _header(skill: Skill) -> str:
    """The name, the description and the files that travel with the skill."""
    parts = [f"<h1>{escape(skill.name)}</h1>"]
    if skill.description:
        parts.append(f"<p><i>{escape(skill.description)}</i></p>")
    parts.append(_source(skill))
    fields = _fields(skill)
    if fields:
        parts.append(fields)
    companions = _companions(skill)
    if companions:
        parts.append(companions)
    parts.append("<hr>")
    return "".join(parts)


def _source(skill: Skill) -> str:
    """The plugin a skill came with, where it came with one."""
    if not skill.source_name:
        return ""
    return f"<p><i>From the {escape(skill.source_name)} plugin</i></p>"


def _fields(skill: Skill) -> str:
    """The short frontmatter this skill declares, beyond the two already shown."""
    rows = [
        f"<li><b>{escape(key)}</b>: {escape(value)}</li>"
        for key, value in skill.header_fields
    ]
    return "" if not rows else "<ul>" + "".join(rows) + "</ul>"


def _long_fields(skill: Skill) -> str:
    """Every oversized frontmatter value, each under a heading of its own.

    These follow the body rather than heading it, so the document a reader
    opened the skill for is the first thing they meet.
    """
    if not skill.long_fields:
        return ""
    sections = "".join(
        f"<h2>{escape(key)}</h2><p>{escape(value)}</p>"
        for key, value in skill.long_fields
    )
    return "<hr>" + sections


def _companions(skill: Skill) -> str:
    """The files beside the document, named so a multi-file skill says so."""
    if not skill.companions:
        return ""
    names = "".join(
        f"<li>{escape(path.rsplit('/', 1)[-1].rsplit(chr(92), 1)[-1])}</li>"
        for path in skill.companions
    )
    return f"<p><b>Files beside this skill</b></p><ul>{names}</ul>"
