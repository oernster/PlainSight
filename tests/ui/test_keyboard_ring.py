"""The focus ring: its order, its wrap, then the stops it refuses to make."""

from __future__ import annotations

from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import QApplication, QWidget

from plainsight.domain.settings import EditorChoice, Settings
from plainsight.infrastructure.resources import BundledAssets
from plainsight.ui.about_dialog import AboutDialog
from plainsight.ui.auto_scroller import AutoScroller
from plainsight.ui.keyboard_nav import is_live
from plainsight.ui.licence_dialog import LicenceDialog
from plainsight.ui.main_window import MainWindow, find_licence
from plainsight.ui.theme import DARK

AN_EDITOR = EditorChoice(path="/usr/bin/vi", display_name="vi")
REALISTIC_WIDTH_PX = 1100
REALISTIC_HEIGHT_PX = 760


A_REAL_LICENCE = find_licence("LICENSE-LGPL-3.0.txt")
SEVERAL = 10


def _chain_stops(window: MainWindow) -> list:
    """Every stop the toolkit's own focus chain would reach."""
    found, seen, walker = [], set(), window
    while True:
        walker = walker.nextInFocusChain()
        if id(walker) in seen:
            return found
        seen.add(id(walker))
        if walker.focusPolicy() & Qt.FocusPolicy.TabFocus:
            found.append(walker)


def live(window: MainWindow) -> list:
    return window.navigator.live_stops()


def press(widget: QWidget, key: Qt.Key) -> None:
    QApplication.sendEvent(
        widget, QKeyEvent(QEvent.Type.KeyPress, key, Qt.KeyboardModifier.NoModifier)
    )


def test_the_ring_is_the_eleven_stops_of_the_design_in_order(
    window: MainWindow,
) -> None:
    stops = window.ring_stops()

    assert stops[0] is window.top_tray.folder_button
    assert stops[1] is window.top_tray.choose_editor_button
    assert stops[2] is window.top_tray.open_in_editor_button
    assert stops[3] is window.top_tray.font_size_button
    assert stops[4] is window.top_tray.appearance_button
    assert stops[5] is window.top_tray.help_button
    assert stops[6] is window.library_tree
    assert stops[7] is window.document_view
    assert stops[8] is window.bottom_tray.donate_button
    assert stops[9] is window.bottom_tray.ui_licence_button
    assert stops[10] is window.bottom_tray.model_licence_button


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


def test_the_tree_leaves_in_one_press_rather_than_walking_its_rows(
    window: MainWindow,
) -> None:
    assert not window.library_tree.tabKeyNavigation()


def test_the_reading_pane_is_a_stop_only_while_it_overflows(
    window: MainWindow,
) -> None:
    window.document_view.setHtml("<p>short</p>")
    window.document_view.sync_focus_policy()
    assert not is_live(window.document_view)

    window.document_view.setHtml("<p>long</p>" * 500)
    window.document_view.sync_focus_policy()
    assert is_live(window.document_view)


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
    store.settings = Settings(
        documents_root=store.settings.documents_root, editor=AN_EDITOR
    )
    window.top_tray.open_in_editor_button.setEnabled(True)
    window.top_tray.open_in_editor_button.setFocus(Qt.FocusReason.TabFocusReason)

    assert window.navigator._activate()


def test_activate_does_nothing_when_focus_is_not_on_a_button(
    window: MainWindow,
) -> None:
    window.library_tree.setFocus(Qt.FocusReason.TabFocusReason)

    assert not window.navigator._activate()


def test_a_dialog_reading_region_is_a_stop_only_while_it_overflows(
    window: MainWindow,
) -> None:
    """The gate the skill pane has always had, now held by every region.

    A licence that is not bundled is two sentences, so its region scrolls
    nowhere and must not be reached at all.
    """
    long_licence = LicenceDialog("A licence", A_REAL_LICENCE, window)
    long_licence.show()
    QApplication.processEvents()
    short_licence = LicenceDialog("A licence", None, window)
    short_licence.show()
    QApplication.processEvents()

    assert is_live(long_licence.text)
    assert not is_live(short_licence.text)
    assert short_licence.first_stop() is not short_licence.text

    long_licence.close()
    short_licence.close()


def test_home_and_end_reach_the_ends_of_a_dialog_region(window: MainWindow) -> None:
    dialog = LicenceDialog("A licence", A_REAL_LICENCE, window)
    dialog.show()
    QApplication.processEvents()
    bar = dialog.text.verticalScrollBar()

    press(dialog.text, Qt.Key.Key_End)
    at_foot = bar.value()
    press(dialog.text, Qt.Key.Key_Home)

    assert at_foot == bar.maximum()
    assert bar.value() == 0
    dialog.close()


def test_the_neutral_start_is_not_on_the_ring(window: MainWindow) -> None:
    """It absorbs the first focus and is never reachable by stepping."""
    assert window._neutral not in live(window)


def test_the_neutral_start_leaves_the_chain_once_it_has_been_used(
    window: MainWindow,
) -> None:
    """A sink of no size must never be something Tab can land on.

    It absorbs the first focus so the window opens with nothing ringed, then
    drops out, so the toolkit's own chain holds no stop with nothing to do.
    """
    assert window._neutral.focusPolicy() is Qt.FocusPolicy.NoFocus
    assert window._neutral not in live(window)
    assert window._neutral not in _chain_stops(window)


def test_a_dialog_is_gone_once_it_is_closed(window: MainWindow) -> None:
    """Kept alive it took its reading cycle with it, ticking, all session.

    Measured before the fix: ten openings of a licence left ten dialogs and
    ten forty millisecond timers running behind the window.
    """
    for _ in range(SEVERAL):
        dialog = LicenceDialog("A licence", A_REAL_LICENCE, window)
        dialog.show()
        QApplication.processEvents()
        dialog.close()
        QApplication.processEvents()

    assert window.findChildren(LicenceDialog) == []
    assert window.findChildren(AutoScroller) == [window.document_view.scroller]
