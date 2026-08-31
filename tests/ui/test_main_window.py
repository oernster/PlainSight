"""The window: what it lists, what it renders and what it enables."""

from __future__ import annotations

from pathlib import Path

from skillsviewer import version
from skillsviewer.domain.settings import EditorChoice, Settings
from skillsviewer.ui.bottom_tray import TRAY_SCALE as BOTTOM_SCALE
from skillsviewer.ui.main_window import (
    NO_BROWSER_MESSAGE,
    NO_EDITOR_MESSAGE,
    MainWindow,
)
from skillsviewer.ui.top_tray import TRAY_SCALE as TOP_SCALE
from skillsviewer.ui.widgets import ICON_SIZE_PX

AN_EDITOR = EditorChoice(path="/usr/bin/vi", display_name="vi")


def test_every_skill_beneath_the_root_is_listed(window: MainWindow) -> None:
    listed = [item.text(0) for item in window.skill_tree.skill_items()]

    assert listed == ["dev", "keeb", "prose"]


def test_the_first_skill_is_selected_and_rendered(window: MainWindow) -> None:
    assert window.skill_tree.selected_skill() is not None
    assert "dev" in window.skill_view.toPlainText()


def test_selecting_another_skill_renders_it(window: MainWindow) -> None:
    window.skill_tree.setCurrentItem(window.skill_tree.skill_items()[2])

    assert "prose" in window.skill_view.toPlainText()


def test_the_view_in_editor_button_starts_disabled(window: MainWindow) -> None:
    assert not window.top_tray.open_in_editor_button.isEnabled()


def test_the_button_enables_once_an_editor_is_chosen_and_present(
    window: MainWindow, store, monkeypatch
) -> None:
    store.settings = Settings(skills_root=store.settings.skills_root, editor=AN_EDITOR)
    monkeypatch.setattr(window._service.probe, "present", {AN_EDITOR.path})

    window.sync_editor_button()

    assert window.top_tray.open_in_editor_button.isEnabled()


def test_opening_hands_the_document_to_the_editor(
    window: MainWindow, store, launcher, monkeypatch
) -> None:
    store.settings = Settings(skills_root=store.settings.skills_root, editor=AN_EDITOR)
    monkeypatch.setattr(window._service.probe, "present", {AN_EDITOR.path})
    window.sync_editor_button()

    window.open_in_editor()

    assert launcher.launched[0][0] == AN_EDITOR
    assert launcher.launched[0][1].endswith("SKILL.md")


def test_an_editor_that_will_not_start_is_reported(
    window: MainWindow, store, launcher
) -> None:
    store.settings = Settings(skills_root=store.settings.skills_root, editor=AN_EDITOR)
    launcher.accepts = False

    window.open_in_editor()

    assert window.statusBar().currentMessage() == NO_EDITOR_MESSAGE


def test_opening_with_nothing_selected_does_nothing(
    window: MainWindow, launcher, store, tmp_path: Path
) -> None:
    """An empty root is the real form of nothing being selected."""
    empty = tmp_path / "empty"
    empty.mkdir()
    store.settings = Settings(skills_root=str(empty))
    window.refresh()

    window.open_in_editor()

    assert window.skill_tree.selected_skill() is None
    assert launcher.launched == []


def test_pressing_donate_asks_the_desktop_for_that_one_address(
    window: MainWindow, opener
) -> None:
    """Asserted literally, so a typo fails here rather than misdirecting money."""
    window.bottom_tray.donate_button.click()

    assert opener.opened == ["https://www.paypal.com/ncp/payment/BCZF8TZTUGTEA"]


def test_the_donation_address_is_handed_over_untouched(
    window: MainWindow, opener, monkeypatch
) -> None:
    address = "https://example.invalid/donate"
    monkeypatch.setattr(version, "DONATE_URL", address)

    window.open_donation()

    assert opener.opened == [address]


def test_a_desktop_that_declines_the_donation_page_is_reported(
    window: MainWindow, opener, monkeypatch
) -> None:
    monkeypatch.setattr(version, "DONATE_URL", "https://example.invalid/donate")
    opener.accepts = False

    window.open_donation()

    assert window.statusBar().currentMessage() == NO_BROWSER_MESSAGE


def test_an_empty_root_invites_the_folder_button(
    window: MainWindow, store, tmp_path: Path
) -> None:
    empty = tmp_path / "empty"
    empty.mkdir()
    store.settings = Settings(skills_root=str(empty))

    window.refresh()

    assert window.skill_tree.skill_items() == []
    assert "folder button" in window.skill_view.toPlainText()


def test_a_skill_that_will_not_read_is_still_listed(
    window: MainWindow, skills_root: Path
) -> None:
    broken = skills_root / "broken"
    broken.mkdir()
    (broken / "SKILL.md").write_bytes(b"\xff\xfe\x00binary")

    window.refresh()

    labels = [item.text(0) for item in window.skill_tree.skill_items()]
    assert "broken (unreadable)" in labels


def test_the_top_tray_reads_larger_than_the_bottom_one(window: MainWindow) -> None:
    """Two trays, read at different distances, so sized apart on purpose."""
    top = window.top_tray.ring_stops()[0]
    bottom = window.bottom_tray.ring_stops()[0]

    assert top.iconSize().width() == round(ICON_SIZE_PX * TOP_SCALE)
    assert bottom.iconSize().width() == round(ICON_SIZE_PX * BOTTOM_SCALE)
    assert top.width() > bottom.width() > 0


def test_opening_a_group_is_carried_into_the_next_run(
    window: MainWindow, store
) -> None:
    """The fixture library has one origin, so the wiring is driven directly."""
    window.skill_tree.groups_changed.emit(("Your skills",))

    assert store.settings.opened_groups == ("Your skills",)


def test_the_tree_is_built_from_the_groups_that_were_left_open(
    window: MainWindow,
) -> None:
    assert window.skill_tree._opened == set(window._service.opened_groups())
