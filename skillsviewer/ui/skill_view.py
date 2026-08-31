"""The reading pane: one skill, rendered, reading itself down the page.

It is a stop on the ring only while it overflows. A page that fits scrolls
nowhere, so focusing it would let the user do nothing.
"""

from __future__ import annotations

from html import escape

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
        self.show_nothing()

    def wear(self, palette: Palette) -> None:
        """Take the colours of this palette; the caller re-renders after.

        Forgetting what is shown is what makes that re-render happen: a
        document keeps the colours it was rendered under, so this is one of the
        two occasions the same skill must genuinely be drawn again.
        """
        self._palette = palette
        self._showing = None
        self.document().setDefaultStyleSheet(document_style(palette))

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
        """Show this content and return the reading cycle to its start hold."""
        self.setHtml(html)
        self.scroller.restart()
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
