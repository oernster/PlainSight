"""The tree filter button: the right end of the bottom tray, one control only.

The picture shows the filter as it stands: the filter picture alone while
``venv``, ``node_modules`` and empty documents are hidden; the same picture
under a red cross while they are shown. The tooltip offers what a press would
do. The cross is laid over the picture at runtime, so there is no composite
artwork.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest
from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QColor, QImage, QKeyEvent, QPixmap
from PySide6.QtWidgets import QApplication

from plainsight.infrastructure.renderer import DocumentHtmlRenderer
from plainsight.infrastructure.resources import BundledAssets
from plainsight.ui import main_window
from plainsight.ui.bottom_tray import (
    HIDE_TOOLTIP,
    NEGATIVE_ICON,
    SHOW_TOOLTIP,
    TREE_FILTER_ICON,
    filter_picture,
    overlaid,
)
from plainsight.ui.main_window import MainWindow

TOOL_FOLDER = "tool"
EMPTY_NOTE = "empty.txt"
A_NOTE = "# Notes\n\nA distinctive sentence.\n"
SIDE_PX = 16
MIDDLE_PX = SIDE_PX // 2
QUARTER_PX = SIDE_PX // 4


@pytest.fixture
def hidden_content(documents_root: Path) -> Path:
    """A folder whose only document sits in its ``venv``; an empty document."""
    package = documents_root / TOOL_FOLDER / "venv" / "lib" / "package"
    package.mkdir(parents=True)
    (package / "package.md").write_text("Body.", encoding="utf-8")
    (documents_root / "prose" / EMPTY_NOTE).write_text("  \n", encoding="utf-8")
    return documents_root


def folder_names(window: MainWindow) -> list[str]:
    """Every folder row's name, without the count beside it."""
    return [item.text(0).split(" (")[0] for item in window.library_tree.folder_items()]


def document_names(window: MainWindow) -> list[str]:
    """Every document row's file name, without any trouble noted beside it."""
    return [item.text(0).split(" ")[0] for item in window.library_tree.document_items()]


def press_the_button(window: MainWindow) -> None:
    window.bottom_tray.filter_button.click()
    QApplication.processEvents()


def test_the_button_is_the_last_thing_in_the_bottom_tray(window: MainWindow) -> None:
    """After the stretch, so it sits at the right end with the others at the left."""
    row = window.bottom_tray.layout()
    last = row.itemAt(row.count() - 1)
    before = row.itemAt(row.count() - 2)

    assert last.widget() is window.bottom_tray.filter_button
    assert before.widget() is None
    assert before.spacerItem() is not None


def test_the_button_ends_the_bottom_tray_ring(window: MainWindow) -> None:
    assert window.bottom_tray.ring_stops()[-1] is window.bottom_tray.filter_button


def test_while_the_filter_is_on_it_offers_to_show_what_it_hides(
    window: MainWindow,
) -> None:
    button = window.bottom_tray.filter_button

    assert SHOW_TOOLTIP == "Show venv, node_modules and empty documents"
    assert button.toolTip() == SHOW_TOOLTIP
    assert button.accessibleName() == SHOW_TOOLTIP


def test_while_the_filter_is_off_it_offers_to_hide_them(window: MainWindow) -> None:
    window.bottom_tray.face_filter(False)
    button = window.bottom_tray.filter_button

    assert HIDE_TOOLTIP == "Hide venv, node_modules and empty documents"
    assert button.toolTip() == HIDE_TOOLTIP
    assert button.accessibleName() == HIDE_TOOLTIP


def comparable(image: QImage) -> QImage:
    """One pixel format, so two routes to the same picture compare equal."""
    return image.convertToFormat(QImage.Format.Format_ARGB32)


def test_the_on_face_is_the_filter_picture_alone(application: QApplication) -> None:
    assets = BundledAssets()

    face = filter_picture(assets, True)

    assert face.toImage() == QPixmap(assets.find(TREE_FILTER_ICON)).toImage()


def test_the_off_face_is_that_picture_with_the_cross_laid_over_it(
    application: QApplication,
) -> None:
    assets = BundledAssets()
    plain = QPixmap(assets.find(TREE_FILTER_ICON))
    crossed = overlaid(plain, QPixmap(assets.find(NEGATIVE_ICON)))

    off = filter_picture(assets, False).toImage()

    assert off == crossed.toImage()
    assert off != plain.toImage()
    assert off.hasAlphaChannel()


def test_the_button_starts_wearing_the_filter_picture_alone(
    window: MainWindow,
) -> None:
    """The filter starts on, so the cross must not be on the button at launch."""
    plain = QPixmap(BundledAssets().find(TREE_FILTER_ICON))
    worn = window.bottom_tray.filter_button.icon().pixmap(plain.size())

    assert comparable(worn.toImage()) == comparable(plain.toImage())


def test_laying_one_picture_over_another_keeps_what_is_clear_in_both(
    application: QApplication,
) -> None:
    """Measured on pictures whose every pixel is known, rather than on artwork."""
    base = QImage(SIDE_PX, SIDE_PX, QImage.Format.Format_ARGB32)
    base.fill(Qt.GlobalColor.transparent)
    base.setPixelColor(QUARTER_PX, QUARTER_PX, QColor("blue"))
    cross = QImage(SIDE_PX, SIDE_PX, QImage.Format.Format_ARGB32)
    cross.fill(Qt.GlobalColor.transparent)
    cross.setPixelColor(MIDDLE_PX, MIDDLE_PX, QColor("red"))

    laid = overlaid(QPixmap.fromImage(base), QPixmap.fromImage(cross)).toImage()

    assert laid.pixelColor(0, 0).alpha() == 0
    assert laid.pixelColor(QUARTER_PX, QUARTER_PX) == QColor("blue")
    assert laid.pixelColor(MIDDLE_PX, MIDDLE_PX) == QColor("red")


def test_pressing_it_turns_the_filter_off_and_lists_what_it_hid(
    window: MainWindow, store, hidden_content: Path
) -> None:
    window.refresh()
    assert TOOL_FOLDER not in folder_names(window)
    assert EMPTY_NOTE not in document_names(window)

    press_the_button(window)

    assert store.settings.filter_tree is False
    assert TOOL_FOLDER in folder_names(window)
    assert "venv" in folder_names(window)
    assert EMPTY_NOTE in document_names(window)
    assert window.bottom_tray.filter_button.toolTip() == HIDE_TOOLTIP


def test_pressing_it_again_hides_them_again(
    window: MainWindow, store, hidden_content: Path
) -> None:
    press_the_button(window)

    press_the_button(window)

    assert store.settings.filter_tree is True
    assert TOOL_FOLDER not in folder_names(window)
    assert EMPTY_NOTE not in document_names(window)
    assert window.bottom_tray.filter_button.toolTip() == SHOW_TOOLTIP


def test_a_folder_left_open_stays_open_across_the_change(
    window: MainWindow, hidden_content: Path
) -> None:
    tree = window.library_tree
    prose = next(item for item in tree.folder_items() if "prose" in item.text(0))
    prose.setExpanded(True)

    press_the_button(window)

    reopened = next(item for item in tree.folder_items() if "prose" in item.text(0))
    assert reopened.isExpanded()


def test_an_opened_file_stays_on_screen_across_the_change(
    window: MainWindow, store, tmp_path: Path, monkeypatch
) -> None:
    """The filter is about walking folders; one file opened is still that file."""
    target = tmp_path / "elsewhere" / "notes.md"
    target.parent.mkdir()
    target.write_text(A_NOTE, encoding="utf-8")
    monkeypatch.setattr(
        main_window.dialogs, "ask_for_document", lambda parent, start: str(target)
    )
    window.open_file()
    QApplication.processEvents()

    press_the_button(window)

    assert store.settings.filter_tree is False
    assert document_names(window) == ["notes.md"]


def test_the_face_follows_the_setting_remembered_from_the_last_run(
    window: MainWindow, store
) -> None:
    store.settings = store.settings.with_filter_tree(False)

    reopened = MainWindow(window.service, DocumentHtmlRenderer(), BundledAssets())

    assert reopened.bottom_tray.filter_button.toolTip() == HIDE_TOOLTIP
    reopened.close()
    reopened.deleteLater()


def test_the_tree_offers_no_menu_of_its_own(window: MainWindow) -> None:
    """One control only: the right-click menu it replaced is gone entirely."""
    policy = window.library_tree.contextMenuPolicy()

    assert policy is Qt.ContextMenuPolicy.DefaultContextMenu
    assert not hasattr(window, "tree_menu")
    assert importlib.util.find_spec("plainsight.ui.tree_menu") is None


@pytest.mark.parametrize(
    ("key", "modifiers"),
    [
        (Qt.Key.Key_Menu, Qt.KeyboardModifier.NoModifier),
        (Qt.Key.Key_F10, Qt.KeyboardModifier.ShiftModifier),
    ],
)
def test_the_menu_keys_open_nothing_on_the_tree(
    window: MainWindow, key: Qt.Key, modifiers: Qt.KeyboardModifier
) -> None:
    tree = window.library_tree
    tree.setFocus(Qt.FocusReason.TabFocusReason)

    QApplication.sendEvent(tree, QKeyEvent(QEvent.Type.KeyPress, key, modifiers))
    QApplication.processEvents()

    assert QApplication.activePopupWidget() is None
