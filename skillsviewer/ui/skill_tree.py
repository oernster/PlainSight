"""The library: one ring stop, walked with Up and Down.

Skills arrive from two places and are shown under a heading for each, with an
arrow that opens and closes the group. Where everything came from one place
there is nothing to separate, so the headings are left out entirely and the
tree reads as the flat list it was.

The arrow is drawn at runtime in the palette's own colour rather than styled or
written as a character. Qt renders a stylesheet triangle as nothing at all and
draws a branch arrow only from an image file; a text glyph would depend on a
font holding it, which could not be verified in this harness. A drawn shape has
neither problem and follows the theme by construction.
"""

from __future__ import annotations

from PySide6.QtCore import QPointF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QIcon, QKeyEvent, QPainter, QPixmap, QPolygonF
from PySide6.QtWidgets import QTreeWidget, QTreeWidgetItem, QWidget

from ..domain.catalogue import SkillCatalogue, SkillGroup
from ..domain.skill import Skill
from .theme import Palette

SKILL_ROLE = int(Qt.ItemDataRole.UserRole)
UNREADABLE_SUFFIX = " (unreadable)"
ONE_GROUP = 1
TOGGLE_KEYS = (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space)
FIRST_COLUMN = 0
ARROW_PX = 12
COUNT_OPENER = " ("

SHUT_POINTS = ((0.30, 0.15), (0.75, 0.50), (0.30, 0.85))
OPEN_POINTS = ((0.15, 0.32), (0.85, 0.32), (0.50, 0.78))


class SkillTree(QTreeWidget):
    """Every skill in the current library, gathered by where it came from."""

    skill_selected = Signal(object)

    def __init__(self, palette: Palette, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("SkillTree")
        self.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        # One stop, not one per cell: Tab must leave the tree in a single press.
        self.setTabKeyNavigation(False)
        self.setHeaderHidden(True)
        self.setColumnCount(1)
        # The arrow is the heading's own icon, so the branch column stays bare.
        self.setRootIsDecorated(False)
        self.setIconSize(QSize(ARROW_PX, ARROW_PX))
        self._palette = palette
        self._selected: Skill | None = None
        self._shut: set[str] = set()
        self.currentItemChanged.connect(self._announce)
        self.itemExpanded.connect(self._remember_open)
        self.itemCollapsed.connect(self._remember_shut)

    def wear(self, palette: Palette) -> None:
        """Take the colours of this palette and redraw the arrows in them."""
        self._palette = palette
        for item in self.headings():
            self._face(item, item.isExpanded())

    def show_catalogue(self, catalogue: SkillCatalogue) -> None:
        """Replace the rows, keeping the selected skill where it survives."""
        previous = self._selected
        self.clear()
        groups = catalogue.groups
        if len(groups) > ONE_GROUP:
            for group in groups:
                self._add_group(group)
        else:
            for skill in catalogue:
                self._add_skill(self, skill)
        self._restore(previous)

    def selected_skill(self) -> Skill | None:
        """The skill last chosen; None when none has been."""
        return self._selected

    def headings(self) -> list[QTreeWidgetItem]:
        """Every top level row that is a heading rather than a skill."""
        tops = (self.topLevelItem(row) for row in range(self.topLevelItemCount()))
        return [top for top in tops if top.data(FIRST_COLUMN, SKILL_ROLE) is None]

    def skill_items(self) -> list[QTreeWidgetItem]:
        """Every row that carries a skill, in the order they are drawn."""
        found: list[QTreeWidgetItem] = []
        for row in range(self.topLevelItemCount()):
            top = self.topLevelItem(row)
            if top.data(FIRST_COLUMN, SKILL_ROLE) is not None:
                found.append(top)
            found.extend(top.child(child) for child in range(top.childCount()))
        return found

    def _add_group(self, group: SkillGroup) -> None:
        """One heading, opened or closed as it was left, then its skills."""
        item = QTreeWidgetItem(self)
        item.setText(FIRST_COLUMN, f"{group.origin.label}{COUNT_OPENER}{len(group)})")
        for skill in group:
            self._add_skill(item, skill)
        item.setExpanded(group.origin.label not in self._shut)
        self._face(item, item.isExpanded())

    def _add_skill(self, parent: QTreeWidget | QTreeWidgetItem, skill: Skill) -> None:
        item = QTreeWidgetItem(parent)
        item.setText(FIRST_COLUMN, _label(skill))
        item.setData(FIRST_COLUMN, SKILL_ROLE, skill)
        item.setToolTip(FIRST_COLUMN, skill.description or skill.name)

    def _face(self, item: QTreeWidgetItem, is_open: bool) -> None:
        """Give a heading the arrow for the state it is in."""
        item.setIcon(FIRST_COLUMN, arrow_icon(self._palette.muted, is_open))

    def _restore(self, previous: Skill | None) -> None:
        """Select the skill that was selected, else the first one there is."""
        items = self.skill_items()
        if not items:
            self._selected = None
            return
        wanted = None if previous is None else previous.document_path
        for item in items:
            if item.data(FIRST_COLUMN, SKILL_ROLE).document_path == wanted:
                self._select(item)
                return
        self._selected = None
        self._select(items[0])

    def _select(self, item: QTreeWidgetItem) -> None:
        """Make this the current row, unless its group is shut.

        Qt opens a group to reach a row inside it, which would undo the reader's
        own decision to close it every time the library is read again. A row
        that cannot be reached is left alone rather than dragged into view.
        """
        parent = item.parent()
        if parent is None or parent.isExpanded():
            self.setCurrentItem(item)

    def _announce(
        self, current: QTreeWidgetItem | None, _previous: QTreeWidgetItem | None
    ) -> None:
        """Report a skill; a heading changes nothing the reader is looking at."""
        skill = None if current is None else current.data(FIRST_COLUMN, SKILL_ROLE)
        if skill is None:
            return
        self._selected = skill
        self.skill_selected.emit(skill)

    def _remember_open(self, item: QTreeWidgetItem) -> None:
        self._shut.discard(_heading_label(item))
        self._face(item, True)

    def _remember_shut(self, item: QTreeWidgetItem) -> None:
        self._shut.add(_heading_label(item))
        self._face(item, False)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """Enter and Space open and close a heading.

        The horizontal arrows step the window's ring everywhere, so they cannot
        also be the tree's own open and close keys; these take their place.
        """
        current = self.currentItem()
        heading = current is not None and current.data(FIRST_COLUMN, SKILL_ROLE) is None
        if heading and event.key() in TOGGLE_KEYS:
            current.setExpanded(not current.isExpanded())
            event.accept()
            return
        super().keyPressEvent(event)


def arrow_icon(colour: str, is_open: bool) -> QIcon:
    """A triangle pointing down while a group is open and right while it is shut."""
    points = OPEN_POINTS if is_open else SHUT_POINTS
    pixmap = QPixmap(ARROW_PX, ARROW_PX)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(QColor(colour))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawPolygon(
        QPolygonF([QPointF(x * ARROW_PX, y * ARROW_PX) for x, y in points])
    )
    painter.end()
    return QIcon(pixmap)


def _heading_label(item: QTreeWidgetItem) -> str:
    """The origin name inside a heading, without the count after it."""
    return item.text(FIRST_COLUMN).rsplit(COUNT_OPENER, 1)[0]


def _label(skill: Skill) -> str:
    """The row's text: the name, the plugin it came with, then any trouble."""
    named = skill.name
    if skill.source_name:
        named = f"{named} ({skill.source_name})"
    return named if skill.is_readable else f"{named}{UNREADABLE_SUFFIX}"
