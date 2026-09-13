"""The folder tree's own menu: whether environment folders are shown.

One checkable action. It is ticked from the saved setting every time the menu
opens rather than once when it is built, so the menu can never show a choice
other than the one that is remembered. The tree says when a menu is wanted, by
a right-click, the menu key or Shift+F10; this only listens.
"""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QObject, QPoint
from PySide6.QtWidgets import QMenu, QTreeWidget

SHOW_ENVIRONMENT_FOLDERS_TEXT = "Show venv and node_modules folders"


class TreeMenu(QObject):
    """The menu a request from the tree pops, holding the one choice."""

    def __init__(
        self,
        tree: QTreeWidget,
        is_shown: Callable[[], bool],
        on_change: Callable[[bool], None],
    ) -> None:
        super().__init__(tree)
        self._tree = tree
        self._is_shown = is_shown
        self._on_change = on_change
        self.menu = QMenu(tree)
        self.action = self.menu.addAction(SHOW_ENVIRONMENT_FOLDERS_TEXT)
        self.action.setCheckable(True)
        self.action.triggered.connect(self._changed)
        tree.customContextMenuRequested.connect(self.open_at)

    def open_at(self, position: QPoint) -> None:
        """Tick the action from what is saved, then pop the menu here.

        The position is in the viewport's terms, which is how a scroll area
        reports every context menu request it raises.
        """
        self.action.setChecked(self._is_shown())
        self.menu.popup(self._tree.viewport().mapToGlobal(position))

    def _changed(self, checked: bool) -> None:
        """Hand the reader's new choice to whoever saves it and reads again."""
        self._on_change(checked)
