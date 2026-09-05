"""The window: what it lists, what it renders and what it enables."""

from __future__ import annotations

from pathlib import Path

from plainsight import version
from plainsight.domain.settings import EditorChoice, Settings
from plainsight.ui.bottom_tray import TRAY_SCALE as BOTTOM_SCALE
from plainsight.ui.main_window import (
    NO_BROWSER_MESSAGE,
    NO_EDITOR_MESSAGE,
    MainWindow,
)
from plainsight.ui.top_tray import TRAY_SCALE as TOP_SCALE
from plainsight.ui.widgets import ICON_SIZE_PX

AN_EDITOR = EditorChoice(path="/usr/bin/vi", display_name="vi")


def select(window: MainWindow, row: int) -> None:
    """Open every folder, then choose one document, as a reader would."""
    for item in window.library_tree.folder_items():
        item.setExpanded(True)
    window.library_tree.setCurrentItem(window.library_tree.document_items()[row])


def test_every_document_beneath_the_root_is_listed_under_its_folder(
    window: MainWindow,
) -> None:
    """The rows carry file names now; the folders carry the skill names."""
    folders = [item.text(0) for item in window.library_tree.folder_items()]
    documents = [item.text(0) for item in window.library_tree.document_items()]

    assert folders == ["skills (3)", "dev (1)", "keeb (1)", "prose (1)"]
    assert documents == ["SKILL.md", "SKILL.md", "SKILL.md"]


def test_nothing_is_selected_or_rendered_until_the_reader_chooses(
    window: MainWindow,
) -> None:
    """No default document, so the pane is not reading one nobody opened."""
    assert window.library_tree.selected_document() is None
    assert "Select a document" in window.document_view.toPlainText()


def test_selecting_a_document_renders_it(window: MainWindow) -> None:
    select(window, 2)

    assert "prose" in window.document_view.toPlainText()


def test_selecting_another_document_renders_that_one_instead(
    window: MainWindow,
) -> None:
    select(window, 2)
    select(window, 0)

    assert "dev" in window.document_view.toPlainText()


def test_the_view_in_editor_button_starts_disabled(window: MainWindow) -> None:
    assert not window.top_tray.open_in_editor_button.isEnabled()


def test_the_button_enables_once_an_editor_is_chosen_and_present(
    window: MainWindow, store, monkeypatch
) -> None:
    store.settings = Settings(
        documents_root=store.settings.documents_root, editor=AN_EDITOR
    )
    monkeypatch.setattr(window._service.probe, "present", {AN_EDITOR.path})
    select(window, 0)

    window.sync_editor_button()

    assert window.top_tray.open_in_editor_button.isEnabled()


def test_opening_hands_the_document_to_the_editor(
    window: MainWindow, store, launcher, monkeypatch
) -> None:
    store.settings = Settings(
        documents_root=store.settings.documents_root, editor=AN_EDITOR
    )
    monkeypatch.setattr(window._service.probe, "present", {AN_EDITOR.path})
    select(window, 0)
    window.sync_editor_button()

    window.open_in_editor()

    assert launcher.launched[0][0] == AN_EDITOR
    assert launcher.launched[0][1].endswith("SKILL.md")


def test_an_editor_that_will_not_start_is_reported(
    window: MainWindow, store, launcher
) -> None:
    store.settings = Settings(
        documents_root=store.settings.documents_root, editor=AN_EDITOR
    )
    launcher.accepts = False
    select(window, 0)

    window.open_in_editor()

    assert window.statusBar().currentMessage() == NO_EDITOR_MESSAGE


def test_opening_with_nothing_selected_does_nothing(
    window: MainWindow, launcher, store, tmp_path: Path
) -> None:
    """An empty root is the real form of nothing being selected."""
    empty = tmp_path / "empty"
    empty.mkdir()
    store.settings = Settings(documents_root=str(empty))
    window.refresh()

    window.open_in_editor()

    assert window.library_tree.selected_document() is None
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
    store.settings = Settings(documents_root=str(empty))

    window.refresh()

    assert window.library_tree.document_items() == []
    assert "folder button" in window.document_view.toPlainText()


def test_a_document_that_will_not_read_is_still_listed(
    window: MainWindow, documents_root: Path
) -> None:
    broken = documents_root / "broken"
    broken.mkdir()
    (broken / "SKILL.md").write_bytes(b"\xff\xfe\x00binary")

    window.refresh()

    labels = [item.text(0) for item in window.library_tree.document_items()]
    assert "SKILL.md (unreadable)" in labels


def test_the_top_tray_reads_larger_than_the_bottom_one(window: MainWindow) -> None:
    """Two trays, read at different distances, so sized apart on purpose."""
    top = window.top_tray.ring_stops()[0]
    bottom = window.bottom_tray.ring_stops()[0]

    assert top.iconSize().width() == round(ICON_SIZE_PX * TOP_SCALE)
    assert bottom.iconSize().width() == round(ICON_SIZE_PX * BOTTOM_SCALE)
    assert top.width() > bottom.width() > 0


def test_opening_a_folder_is_carried_into_the_next_run(
    window: MainWindow, store
) -> None:
    """Driven through the signal, which is the wiring under test."""
    window.library_tree.folders_changed.emit(("/skills/prose",))

    assert store.settings.opened_folders == ("/skills/prose",)


def test_the_tree_is_built_from_the_folders_that_were_left_open(
    window: MainWindow,
) -> None:
    assert window.library_tree._opened == set(window._service.opened_folders())


def test_present_puts_the_window_up_rather_than_only_showing_it(
    window: MainWindow,
) -> None:
    """Reported after a fresh install: it opened behind everything else.

    Offscreen cannot settle stacking or real foreground activation, so this
    asserts the mechanism rather than the outcome: the window is up, it is not
    minimised, then that `present` is what the composition root calls. Whether it
    actually comes to the front is a question only the real desktop answers.
    """
    window.hide()

    window.present()

    assert window.isVisible()
    assert not window.isMinimized()


def test_the_composition_root_presents_rather_than_shows() -> None:
    """A bare show() is the defect, so it must not creep back in.

    Read from the source rather than by running it: main() enters the Qt event
    loop and never returns, so it cannot be called from a test.
    """
    root = (
        Path(__file__).resolve().parents[2] / "plainsight" / "__main__.py"
    ).read_text(encoding="utf-8")

    assert "window.present()" in root
    assert "window.show()" not in root
