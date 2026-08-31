"""The reading pane: one skill, rendered, reading itself down the page.

It is a stop on the ring only while it overflows. A page that fits scrolls
nowhere, so focusing it would let the user do nothing.
"""

from __future__ import annotations

from html import escape

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QTextBrowser, QWidget

from ..application.ports import MarkdownRenderer
from ..domain.skill import Skill
from .auto_scroller import AutoScroller
from .theme import Palette, document_style

NO_OVERFLOW = 0
EMPTY_MESSAGE = (
    "<h2>No skills here</h2>"
    "<p>Nothing beneath this folder holds a SKILL.md. "
    "Use the folder button to browse somewhere else.</p>"
)
NOTHING_SELECTED = "<h2>Select a skill</h2><p>Pick one from the list to read it.</p>"


class SkillView(QTextBrowser):
    """A rendered skill, with the reading cycle attached."""

    def __init__(
        self,
        renderer: MarkdownRenderer,
        palette: Palette,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("SkillView")
        self.setOpenExternalLinks(True)
        self.setReadOnly(True)
        self.document().setDefaultStyleSheet(document_style(palette))
        self._renderer = renderer
        self._palette = palette
        self._scroller = AutoScroller(self)
        self.show_nothing()

    def wear(self, palette: Palette) -> None:
        """Take the colours of this palette; the caller re-renders after."""
        self._palette = palette
        self.document().setDefaultStyleSheet(document_style(palette))

    @property
    def scroller(self) -> AutoScroller:
        """The reading cycle, for tests and for the window to restart."""
        return self._scroller

    def show_nothing(self) -> None:
        """The state before a skill has been picked."""
        self._set(NOTHING_SELECTED)

    def show_empty_root(self) -> None:
        """The state when the chosen folder holds no skills."""
        self._set(EMPTY_MESSAGE)

    def show_skill(self, skill: Skill) -> None:
        """Render one skill: its header, then its body or its failure."""
        self._set(_header(skill) + self._body(skill))

    def _body(self, skill: Skill) -> str:
        if not skill.is_readable:
            return f"<p><b>{escape(skill.failure)}</b></p>"
        return self._renderer.render(skill.body)

    def _set(self, html: str) -> None:
        """Show this content and return the reading cycle to its start hold."""
        self.setHtml(html)
        self._scroller.restart()
        self.sync_focus_policy()

    def sync_focus_policy(self) -> None:
        """A stop while it overflows; never otherwise."""
        overflows = self.verticalScrollBar().maximum() > NO_OVERFLOW
        self.setFocusPolicy(
            Qt.FocusPolicy.TabFocus if overflows else Qt.FocusPolicy.NoFocus
        )

    def resizeEvent(self, event: object) -> None:
        super().resizeEvent(event)  # type: ignore[arg-type]
        self.sync_focus_policy()


def _header(skill: Skill) -> str:
    """The name, the description and the files that travel with the skill."""
    parts = [f"<h1>{escape(skill.name)}</h1>"]
    if skill.description:
        parts.append(f"<p><i>{escape(skill.description)}</i></p>")
    fields = _fields(skill)
    if fields:
        parts.append(fields)
    companions = _companions(skill)
    if companions:
        parts.append(companions)
    parts.append("<hr>")
    return "".join(parts)


def _fields(skill: Skill) -> str:
    """The frontmatter this skill declares, beyond the two already shown."""
    shown = {"name", "description"}
    rows = [
        f"<li><b>{escape(key)}</b>: {escape(value)}</li>"
        for key, value in skill.declared_fields
        if key not in shown
    ]
    return "" if not rows else "<ul>" + "".join(rows) + "</ul>"


def _companions(skill: Skill) -> str:
    """The files beside the document, named so a multi-file skill says so."""
    if not skill.companions:
        return ""
    names = "".join(
        f"<li>{escape(path.rsplit('/', 1)[-1].rsplit(chr(92), 1)[-1])}</li>"
        for path in skill.companions
    )
    return f"<p><b>Files beside this skill</b></p><ul>{names}</ul>"
