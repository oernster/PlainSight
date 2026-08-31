"""The list of skills: one ring stop, walked with Up and Down.

An item view takes no ring in any state. Its current row is the indicator, so a
rectangle round the whole view would outline everything while selecting nothing.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QListWidget, QListWidgetItem, QWidget

from ..domain.catalogue import SkillCatalogue
from ..domain.skill import Skill

SKILL_ROLE = int(Qt.ItemDataRole.UserRole)
NO_SELECTION = -1
UNREADABLE_SUFFIX = " (unreadable)"


class SkillList(QListWidget):
    """Every skill in the current root, in display order."""

    skill_selected = Signal(object)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("SkillList")
        self.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        # One stop, not one per cell: Tab must leave the list in a single press.
        self.setTabKeyNavigation(False)
        self.setUniformItemSizes(True)
        self.currentItemChanged.connect(self._announce)

    def show_catalogue(self, catalogue: SkillCatalogue) -> None:
        """Replace the rows, keeping the selected skill where it survives."""
        previous = self.selected_skill()
        self.clear()
        for skill in catalogue:
            item = QListWidgetItem(_label(skill), self)
            item.setData(SKILL_ROLE, skill)
            item.setToolTip(skill.description or skill.name)
        self._restore(previous)

    def selected_skill(self) -> Skill | None:
        """The skill on the current row; None when no row is current."""
        item = self.currentItem()
        return None if item is None else item.data(SKILL_ROLE)

    def _restore(self, previous: Skill | None) -> None:
        """Select the skill that was selected, else the first row."""
        if self.count() == 0:
            return
        wanted = None if previous is None else previous.name
        for row in range(self.count()):
            if self.item(row).data(SKILL_ROLE).name == wanted:
                self.setCurrentRow(row)
                return
        self.setCurrentRow(0)

    def _announce(
        self, current: QListWidgetItem | None, _previous: QListWidgetItem | None
    ) -> None:
        self.skill_selected.emit(None if current is None else current.data(SKILL_ROLE))


def _label(skill: Skill) -> str:
    """The row's text: the name, marked where its document would not read."""
    return skill.name if skill.is_readable else f"{skill.name}{UNREADABLE_SUFFIX}"
