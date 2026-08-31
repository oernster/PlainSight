"""The setup window: which screen shows, then what its footer offers.

Nothing here calls begin: these tests drive the window's shape, never its work,
so no test can install or remove anything on the machine running them.
"""

from __future__ import annotations

import pathlib
from collections.abc import Iterator

import pytest
from PySide6.QtCore import QRect, Qt
from PySide6.QtWidgets import QApplication, QCheckBox, QLabel, QPushButton

from installer import screens, theme
from installer.app import SetupWindow
from installer.existing import Existing
from installer.footer import DANGER, PRIMARY
from installer.route import Route

UNBOUNDED_PX = 10000
WIDENED_PX = 200


def one_label(window: SetupWindow, name: str) -> QLabel:
    """The single label carrying this object name."""
    found = [c for c in window.findChildren(QLabel) if c.objectName() == name]
    assert len(found) == 1
    return found[0]


A_VERSION = "1.2.0"


@pytest.fixture
def window(application: QApplication, monkeypatch) -> Iterator[SetupWindow]:
    """A window over a machine with nothing installed."""
    monkeypatch.setattr(
        "installer.app.look",
        lambda: Existing("", pathlib.Path("C:/nowhere"), False, False),
    )
    made = SetupWindow(uninstalling=False)
    made.show()
    yield made
    made.close()


def installed_window(monkeypatch, version: str) -> SetupWindow:
    """A window over a machine that already has this version."""
    monkeypatch.setattr(
        "installer.app.look",
        lambda: Existing(version, pathlib.Path("C:/nowhere"), True, False),
    )
    monkeypatch.setattr("installer.app.read_version", lambda: A_VERSION)
    return SetupWindow(uninstalling=False)


def labels(window: SetupWindow) -> list[str]:
    return [button.text() for button in window.footer.buttons()]


def test_it_opens_on_the_route_screen(window: SetupWindow) -> None:
    assert window.stack.currentIndex() == screens.ROUTE_SCREEN


def test_nothing_installed_is_an_install(window: SetupWindow) -> None:
    assert window.route is Route.INSTALL
    assert "Install" in labels(window)


def test_removal_is_not_offered_when_there_is_nothing_to_remove(
    window: SetupWindow,
) -> None:
    assert "Remove" not in labels(window)


def test_removal_is_offered_once_something_is_installed(
    application: QApplication, monkeypatch
) -> None:
    made = installed_window(monkeypatch, A_VERSION)
    try:
        assert "Remove" in labels(made)
    finally:
        made.close()


def test_the_same_version_leaves_nothing_to_install(
    application: QApplication, monkeypatch
) -> None:
    made = installed_window(monkeypatch, A_VERSION)
    try:
        assert made.route is Route.MANAGE
        assert "Repair" in labels(made)
        assert "Reinstall" in labels(made)
    finally:
        made.close()


def test_the_uninstall_screen_is_reachable_without_becoming_the_route(
    application: QApplication, monkeypatch
) -> None:
    """Removal is a screen, so the screen behind it stays the one to return to."""
    made = installed_window(monkeypatch, A_VERSION)
    try:
        made.show_uninstall()

        assert made.stack.currentIndex() == screens.UNINSTALL_SCREEN
        assert made.route is Route.MANAGE
        assert "Cancel" in labels(made)
    finally:
        made.close()


def test_cancelling_removal_returns_to_the_route_screen(
    application: QApplication, monkeypatch
) -> None:
    made = installed_window(monkeypatch, A_VERSION)
    try:
        made.show_uninstall()
        made.show_route()

        assert made.stack.currentIndex() == screens.ROUTE_SCREEN
    finally:
        made.close()


def test_the_removal_go_ahead_reads_as_destructive(
    application: QApplication, monkeypatch
) -> None:
    made = installed_window(monkeypatch, A_VERSION)
    try:
        made.show_uninstall()
        kinds = [button.objectName() for button in made.footer.buttons()]

        assert DANGER in kinds
    finally:
        made.close()


def test_the_progress_screen_offers_nothing_at_all(window: SetupWindow) -> None:
    """A screen with nothing safe to offer offers nothing."""
    window.perform(())

    assert window.stack.currentIndex() == screens.PROGRESS_SCREEN
    assert window.footer.buttons() == ()


def test_the_old_footer_buttons_are_unparented_not_only_deleted(
    window: SetupWindow,
) -> None:
    """A button awaiting deletion is still a child, still laid out and drawn."""
    before = window.footer.buttons()
    window.footer.show_actions(())

    assert [button for button in before if button.parent() is window.footer] == []


def test_the_options_open_on_what_is_already_true(
    application: QApplication, monkeypatch
) -> None:
    monkeypatch.setattr(
        "installer.app.look",
        lambda: Existing(A_VERSION, pathlib.Path("C:/nowhere"), True, False),
    )
    made = SetupWindow(uninstalling=False)
    try:
        assert made.route_screen.desktop.isChecked()
        assert not made.route_screen.start_menu.isChecked()
    finally:
        made.close()


def test_nothing_is_disabled_in_place_while_work_runs(window: SetupWindow) -> None:
    """An operation moves to a screen; it never greys the options where they are."""
    window.perform(())

    boxes = window.route_screen.widget.findChildren(QCheckBox)
    assert [box for box in boxes if not box.isEnabled()] == []
    assert not window.route_screen.widget.isVisible()


def test_it_starts_neutral(window: SetupWindow) -> None:
    assert window.focusWidget() is window._neutral


def test_no_container_is_a_focus_stop(window: SetupWindow) -> None:
    assert window.stack.focusPolicy().name == "NoFocus"
    assert window.footer.focusPolicy().name == "NoFocus"


def test_the_header_carries_no_version(window: SetupWindow) -> None:
    """A version has no baseline beside a 32px title; it belongs in the body."""
    from PySide6.QtWidgets import QLabel

    titles = [
        label.text()
        for label in window.findChildren(QLabel)
        if label.objectName() in ("Title", "Tagline")
    ]

    assert [text for text in titles if "v" + window.version in text] == []


def test_the_body_names_the_version_instead(window: SetupWindow) -> None:
    assert window.version in window.route_screen.flow.text()


def test_the_mark_is_the_house_size() -> None:
    assert theme.MARK_PX == 126


def test_the_appearance_toggle_is_artwork_rather_than_a_text_pill(
    window: SetupWindow,
) -> None:
    """The licence is text and the toggle is a picture, deliberately."""
    assert window.theme_button.text() == ""
    assert not window.theme_button.icon().isNull()
    assert window.licence_button.text() == "Licence"


def test_the_appearance_toggle_says_what_it_would_move_to(
    window: SetupWindow,
) -> None:
    """Repaint and re-face happen together; a lagging toggle invites a second press."""
    from installer.app import TO_DARK_TOOLTIP, TO_LIGHT_TOOLTIP

    assert window.theme_button.toolTip() == TO_LIGHT_TOOLTIP

    window.switch_appearance()

    assert window.palette_choice is theme.LIGHT
    assert window.theme_button.toolTip() == TO_DARK_TOOLTIP


def test_the_toggle_wears_a_different_mark_in_each_appearance(
    window: SetupWindow,
) -> None:
    dark_face = window.theme_button.icon().cacheKey()

    window.switch_appearance()

    assert window.theme_button.icon().cacheKey() != dark_face


def test_the_toggle_carries_its_own_ring_rule() -> None:
    """An object-name border rule beats the generic one by id specificity."""
    sheet = theme.stylesheet(theme.DARK)

    assert "QPushButton#Mark:enabled:hover" in sheet
    assert "QPushButton#Mark:enabled:focus" in sheet


def test_every_named_button_carries_its_own_ring_rule() -> None:
    """An object-name border rule beats the generic one by id specificity."""
    sheet = theme.stylesheet(theme.DARK)

    for name in (PRIMARY, DANGER, "Link"):
        assert f"QPushButton#{name}:enabled:hover" in sheet
        assert f"QPushButton#{name}:enabled:focus" in sheet


def test_the_accent_is_never_a_ring() -> None:
    """It carries identity, so it never carries state as well."""
    for palette in (theme.DARK, theme.LIGHT):
        assert palette.ring != palette.accent
        assert palette.danger != palette.accent


def test_a_disabled_control_paints_the_permanent_danger_ring() -> None:
    sheet = theme.stylesheet(theme.DARK)

    assert "QPushButton:disabled" in sheet
    assert theme.DARK.danger in sheet.split("QPushButton:disabled")[1][:200]


def test_the_footer_is_rebuilt_rather_than_relabelled(window: SetupWindow) -> None:
    before = window.footer.buttons()
    window.show_uninstall()
    after = window.footer.buttons()

    assert [button for button in after if button in before] == []
    assert all(isinstance(button, QPushButton) for button in after)


def test_the_tagline_is_given_the_whole_line_beside_the_mark(
    window: SetupWindow,
) -> None:
    """It reads across the header rather than being boxed under the name.

    Confined to the width of the name above it, the tagline broke early and
    stranded its last word while the room it needed sat unused beside the
    controls. The width is asserted against the title rather than a pixel
    figure, since the font differs between this harness and a real desktop.
    """
    tagline = one_label(window, "Tagline")
    title = one_label(window, "Title")

    assert tagline.width() > title.width()


def test_the_tagline_reads_on_a_single_line(window: SetupWindow) -> None:
    """Measured from the laid out text, not from the box the layout gives it."""
    tagline = one_label(window, "Tagline")
    metrics = tagline.fontMetrics()
    wrapped = metrics.boundingRect(
        QRect(0, 0, tagline.width(), UNBOUNDED_PX),
        Qt.TextFlag.TextWordWrap,
        tagline.text(),
    )

    assert wrapped.height() == metrics.height()


def test_the_tagline_sits_under_the_name(window: SetupWindow) -> None:
    assert one_label(window, "Tagline").y() > one_label(window, "Title").y()


def test_a_wider_window_gives_the_tagline_the_extra_room(
    window: SetupWindow,
) -> None:
    """The names column takes the room left over rather than a bare stretch."""
    tagline = one_label(window, "Tagline")
    narrow = tagline.width()

    window.resize(window.width() + WIDENED_PX, window.height())
    QApplication.processEvents()

    assert tagline.width() > narrow
