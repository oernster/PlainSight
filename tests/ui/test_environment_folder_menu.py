"""The folder tree's own menu: whether ``venv`` and ``node_modules`` are shown.

The menu is opened three ways and each is driven here rather than assumed. A
right-click arrives as a context menu event. The menu key and Shift+F10 were
measured offscreen raising no context menu event at all, whether sent to the
tree or through its window, so the tree answers those two keys itself.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtCore import QEvent, QPoint, Qt
from PySide6.QtGui import QContextMenuEvent, QKeyEvent
from PySide6.QtWidgets import QApplication

from plainsight.ui import main_window
from plainsight.ui.main_window import MainWindow
from plainsight.ui.tree_menu import SHOW_ENVIRONMENT_FOLDERS_TEXT

TOOL_FOLDER = "tool"
A_POINT_IN_THE_TREE = QPoint(5, 5)
A_NOTE = "# Notes\n\nA distinctive sentence.\n"


@pytest.fixture
def environment(documents_root: Path) -> Path:
    """A folder whose only document sits inside its ``venv``."""
    package = documents_root / TOOL_FOLDER / "venv" / "lib" / "package"
    package.mkdir(parents=True)
    (package / "package.md").write_text("Body.", encoding="utf-8")
    return package


def folder_names(window: MainWindow) -> list[str]:
    """Every folder row's name, without the count beside it."""
    return [item.text(0).split(" (")[0] for item in window.library_tree.folder_items()]


def open_menu(window: MainWindow) -> None:
    """Ask for the menu the way the tree does, at a point inside it."""
    window.library_tree.customContextMenuRequested.emit(A_POINT_IN_THE_TREE)
    QApplication.processEvents()


def press(window: MainWindow, key: Qt.Key, modifiers: Qt.KeyboardModifier) -> None:
    tree = window.library_tree
    tree.setFocus(Qt.FocusReason.TabFocusReason)
    QApplication.sendEvent(tree, QKeyEvent(QEvent.Type.KeyPress, key, modifiers))
    QApplication.processEvents()


def test_the_tree_asks_for_a_menu_of_its_own(window: MainWindow) -> None:
    policy = window.library_tree.contextMenuPolicy()

    assert policy is Qt.ContextMenuPolicy.CustomContextMenu


@pytest.mark.parametrize(
    "reason", [QContextMenuEvent.Reason.Mouse, QContextMenuEvent.Reason.Keyboard]
)
def test_a_context_menu_event_on_the_tree_opens_the_menu(
    window: MainWindow, reason: QContextMenuEvent.Reason
) -> None:
    """The route a right-click takes; a desktop that turns keys into it too."""
    viewport = window.library_tree.viewport()
    event = QContextMenuEvent(
        reason, A_POINT_IN_THE_TREE, viewport.mapToGlobal(A_POINT_IN_THE_TREE)
    )

    QApplication.sendEvent(viewport, event)
    QApplication.processEvents()

    assert window.tree_menu.menu.isVisible()


def test_the_menu_holds_one_checkable_action_in_exactly_these_words(
    window: MainWindow,
) -> None:
    actions = window.tree_menu.menu.actions()

    assert [action.text() for action in actions] == [
        "Show venv and node_modules folders"
    ]
    assert SHOW_ENVIRONMENT_FOLDERS_TEXT == "Show venv and node_modules folders"
    assert actions[0].isCheckable()


def test_the_action_is_unticked_while_the_folders_are_hidden(
    window: MainWindow,
) -> None:
    open_menu(window)

    assert not window.tree_menu.action.isChecked()


def test_the_action_reads_the_saved_setting_each_time_the_menu_opens(
    window: MainWindow, store
) -> None:
    open_menu(window)
    before = window.tree_menu.action.isChecked()
    window.tree_menu.menu.close()
    store.settings = store.settings.with_show_environment_folders(True)

    open_menu(window)

    assert before is False
    assert window.tree_menu.action.isChecked()


def test_the_folder_inside_venv_is_not_listed_by_default(
    window: MainWindow, environment: Path
) -> None:
    window.refresh()

    assert TOOL_FOLDER not in folder_names(window)


def test_ticking_it_saves_the_setting_and_lists_that_folder(
    window: MainWindow, store, environment: Path
) -> None:
    window.refresh()
    open_menu(window)

    window.tree_menu.action.trigger()
    QApplication.processEvents()

    assert store.settings.show_environment_folders is True
    assert TOOL_FOLDER in folder_names(window)
    assert "venv" in folder_names(window)


def test_unticking_it_hides_that_folder_again(
    window: MainWindow, store, environment: Path
) -> None:
    store.settings = store.settings.with_show_environment_folders(True)
    window.refresh()
    open_menu(window)

    window.tree_menu.action.trigger()
    QApplication.processEvents()

    assert store.settings.show_environment_folders is False
    assert TOOL_FOLDER not in folder_names(window)


def test_a_folder_left_open_stays_open_across_the_change(
    window: MainWindow, environment: Path
) -> None:
    tree = window.library_tree
    prose = next(item for item in tree.folder_items() if "prose" in item.text(0))
    prose.setExpanded(True)
    open_menu(window)

    window.tree_menu.action.trigger()
    QApplication.processEvents()

    reopened = next(item for item in tree.folder_items() if "prose" in item.text(0))
    assert reopened.isExpanded()


def test_the_menu_key_opens_the_menu_on_the_focused_tree(window: MainWindow) -> None:
    press(window, Qt.Key.Key_Menu, Qt.KeyboardModifier.NoModifier)

    assert window.tree_menu.menu.isVisible()


def test_shift_f10_opens_the_menu_on_the_focused_tree(window: MainWindow) -> None:
    press(window, Qt.Key.Key_F10, Qt.KeyboardModifier.ShiftModifier)

    assert window.tree_menu.menu.isVisible()


def test_f10_without_shift_opens_no_menu(window: MainWindow) -> None:
    press(window, Qt.Key.Key_F10, Qt.KeyboardModifier.NoModifier)

    assert not window.tree_menu.menu.isVisible()


def test_an_opened_file_stays_on_screen_across_the_change(
    window: MainWindow, store, tmp_path: Path, monkeypatch
) -> None:
    """The setting is about walking folders; one file opened is still that file."""
    target = tmp_path / "elsewhere" / "notes.md"
    target.parent.mkdir()
    target.write_text(A_NOTE, encoding="utf-8")
    monkeypatch.setattr(
        main_window.dialogs, "ask_for_document", lambda parent, start: str(target)
    )
    window.open_file()
    QApplication.processEvents()
    open_menu(window)

    window.tree_menu.action.trigger()
    QApplication.processEvents()

    rows = [item.text(0) for item in window.library_tree.document_items()]
    assert store.settings.show_environment_folders is True
    assert rows == ["notes.md"]
