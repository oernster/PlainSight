"""The focus ring: its order, its wrap, then the stops it refuses to make."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from skillsviewer.domain.settings import EditorChoice, Settings
from skillsviewer.infrastructure.resources import BundledAssets
from skillsviewer.ui.about_dialog import AboutDialog
from skillsviewer.ui.keyboard_nav import is_live
from skillsviewer.ui.licence_dialog import LicenceDialog
from skillsviewer.ui.main_window import MainWindow
from skillsviewer.ui.theme import DARK

AN_EDITOR = EditorChoice(path="/usr/bin/vi", display_name="vi")
REALISTIC_WIDTH_PX = 1100
REALISTIC_HEIGHT_PX = 760


def live(window: MainWindow) -> list:
    return window.navigator.live_stops()


def test_the_ring_is_the_ten_stops_of_the_design_in_order(
    window: MainWindow,
) -> None:
    stops = window.ring_stops()

    assert stops[0] is window.top_tray.folder_button
    assert stops[1] is window.top_tray.choose_editor_button
    assert stops[2] is window.top_tray.open_in_editor_button
    assert stops[3] is window.top_tray.appearance_button
    assert stops[4] is window.top_tray.help_button
    assert stops[5] is window.skill_list
    assert stops[6] is window.skill_view
    assert stops[7] is window.bottom_tray.donate_button
    assert stops[8] is window.bottom_tray.ui_licence_button
    assert stops[9] is window.bottom_tray.model_licence_button


def test_each_tray_declares_its_own_order_left_to_right_as_drawn(
    window: MainWindow,
) -> None:
    window.resize(REALISTIC_WIDTH_PX, REALISTIC_HEIGHT_PX)
    QApplication.processEvents()

    for tray in (window.top_tray, window.bottom_tray):
        for stop in tray.ring_stops():
            stop.setEnabled(True)
        centres = [
            stop.mapTo(window, stop.rect().center()).x() for stop in tray.ring_stops()
        ]
        assert centres == sorted(centres)


def test_every_focusable_child_of_a_tray_is_in_its_declaration(
    window: MainWindow,
) -> None:
    for tray in (window.top_tray, window.bottom_tray):
        declared = {id(stop) for stop in tray.ring_stops()}
        from PySide6.QtWidgets import QPushButton

        children = tray.findChildren(QPushButton)
        assert [child for child in children if id(child) not in declared] == []


def test_a_disabled_stop_is_skipped(window: MainWindow) -> None:
    window.top_tray.open_in_editor_button.setEnabled(False)

    assert window.top_tray.open_in_editor_button not in live(window)


def test_the_ring_wraps_forward_from_the_last_stop(window: MainWindow) -> None:
    stops = live(window)
    stops[-1].setFocus(Qt.FocusReason.TabFocusReason)

    window.navigator._step(1)

    assert QApplication.focusWidget() is stops[0]


def test_the_ring_wraps_back_from_the_first_stop(window: MainWindow) -> None:
    stops = live(window)
    stops[0].setFocus(Qt.FocusReason.TabFocusReason)

    window.navigator._step(-1)

    assert QApplication.focusWidget() is stops[-1]


def test_focus_nowhere_on_the_ring_enters_at_the_first_stop(
    window: MainWindow,
) -> None:
    window._neutral.setFocus(Qt.FocusReason.OtherFocusReason)

    window.navigator._step(1)

    assert QApplication.focusWidget() is live(window)[0]


def test_the_window_starts_neutral(window: MainWindow) -> None:
    assert QApplication.focusWidget() is window._neutral
    assert window._neutral not in window.ring_stops()


def test_the_list_leaves_in_one_press_rather_than_walking_its_rows(
    window: MainWindow,
) -> None:
    assert not window.skill_list.tabKeyNavigation()


def test_the_reading_pane_is_a_stop_only_while_it_overflows(
    window: MainWindow,
) -> None:
    window.skill_view.setHtml("<p>short</p>")
    window.skill_view.sync_focus_policy()
    assert not is_live(window.skill_view)

    window.skill_view.setHtml("<p>long</p>" * 500)
    window.skill_view.sync_focus_policy()
    assert is_live(window.skill_view)


def test_the_about_dialog_opens_on_its_first_stop(window: MainWindow) -> None:
    dialog = AboutDialog(DARK, BundledAssets(), window)
    dialog.show()
    QApplication.processEvents()

    assert dialog.focusWidget() is dialog.first_stop()
    dialog.close()


def test_a_licence_dialog_opens_on_its_first_stop(window: MainWindow) -> None:
    dialog = LicenceDialog("A licence", None, window)
    dialog.show()
    QApplication.processEvents()

    assert dialog.focusWidget() is dialog.first_stop()
    dialog.close()


def test_a_button_activates_on_enter_and_on_space(window: MainWindow, store) -> None:
    store.settings = Settings(skills_root=store.settings.skills_root, editor=AN_EDITOR)
    window.top_tray.open_in_editor_button.setEnabled(True)
    window.top_tray.open_in_editor_button.setFocus(Qt.FocusReason.TabFocusReason)

    assert window.navigator._activate()


def test_activate_does_nothing_when_focus_is_not_on_a_button(
    window: MainWindow,
) -> None:
    window.skill_list.setFocus(Qt.FocusReason.TabFocusReason)

    assert not window.navigator._activate()
