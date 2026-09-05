"""The appearance toggle: where it sits, what it wears and what it changes."""

from __future__ import annotations

from PySide6.QtWidgets import QApplication

from plainsight.domain.settings import Appearance
from plainsight.ui import top_tray
from plainsight.ui.main_window import MainWindow
from plainsight.ui.theme import DARK, LIGHT, palette_for


def test_it_sits_immediately_left_of_help(window: MainWindow) -> None:
    stops = window.top_tray.ring_stops()

    assert stops[stops.index(window.top_tray.help_button) - 1] is (
        window.top_tray.appearance_button
    )


def test_it_is_drawn_left_of_help_as_well_as_ordered_before_it(
    window: MainWindow,
) -> None:
    """Ring order is reading order, so the declaration cannot lie."""
    window.resize(1100, 760)
    QApplication.processEvents()

    def centre(button) -> int:
        return button.mapTo(window, button.rect().center()).x()

    assert centre(window.top_tray.appearance_button) < centre(
        window.top_tray.help_button
    )


def test_it_starts_dark_and_wears_the_sun(window: MainWindow) -> None:
    """It shows the appearance it would move TO, never the current one."""
    assert window._appearance() is Appearance.DARK
    assert window.top_tray.appearance_button.toolTip() == top_tray.TO_LIGHT_TOOLTIP


def test_pressing_it_moves_to_light_and_re_faces_in_the_same_call(
    window: MainWindow,
) -> None:
    window.switch_appearance()

    assert window._appearance() is Appearance.LIGHT
    assert window._palette is LIGHT
    assert window.top_tray.appearance_button.toolTip() == top_tray.TO_DARK_TOOLTIP


def test_pressing_it_twice_returns_to_dark(window: MainWindow) -> None:
    window.switch_appearance()
    window.switch_appearance()

    assert window._palette is DARK
    assert window.top_tray.appearance_button.toolTip() == top_tray.TO_LIGHT_TOOLTIP


def test_the_choice_is_remembered(window: MainWindow, store) -> None:
    window.switch_appearance()

    assert store.settings.appearance is Appearance.LIGHT


def test_a_remembered_light_appearance_opens_light(
    application, documents_root, store, launcher, opener
) -> None:
    from plainsight.__main__ import build_readers
    from plainsight.application.services import LibraryService
    from plainsight.domain.settings import Settings
    from plainsight.infrastructure.document_repository import (
        FileSystemDocumentRepository,
    )
    from plainsight.infrastructure.renderer import DocumentHtmlRenderer
    from plainsight.infrastructure.resources import BundledAssets
    from tests.application.fakes import FakePaths, FakeProbe

    store.settings = Settings(
        documents_root=str(documents_root), appearance=Appearance.LIGHT
    )
    made = MainWindow(
        LibraryService(
            repository=FileSystemDocumentRepository(build_readers()),
            settings_store=store,
            launcher=launcher,
            opener=opener,
            probe=FakeProbe(),
            paths=FakePaths(),
        ),
        DocumentHtmlRenderer(),
        BundledAssets(),
    )
    try:
        assert made._palette is LIGHT
        assert made.top_tray.appearance_button.toolTip() == top_tray.TO_DARK_TOOLTIP
    finally:
        made.close()


def test_the_switch_repaints_the_application(window: MainWindow) -> None:
    before = QApplication.instance().styleSheet()

    window.switch_appearance()

    after = QApplication.instance().styleSheet()
    assert after != before
    assert LIGHT.ring in after


def test_the_open_skill_is_re_rendered_in_the_new_palette(
    window: MainWindow,
) -> None:
    """A document keeps the colours it was rendered under unless it is redone."""
    window.switch_appearance()

    assert LIGHT.accent in window.document_view.document().defaultStyleSheet()
    assert window.document_view.toPlainText().strip() != ""


def test_each_palette_names_its_own_ring_and_danger() -> None:
    """A pastel green that reads on near-black is weak on white."""
    assert DARK.ring != LIGHT.ring
    assert DARK.danger != LIGHT.danger


def test_the_accent_is_never_a_ring_in_either_palette() -> None:
    for palette in (DARK, LIGHT):
        assert palette.accent != palette.ring
        assert palette.accent != palette.danger


def test_both_marks_are_bundled() -> None:
    from plainsight.infrastructure.resources import BundledAssets

    assets = BundledAssets()
    assert assets.find(top_tray.LIGHT_MODE_ICON) is not None
    assert assets.find(top_tray.DARK_MODE_ICON) is not None


def test_palette_for_maps_both_ways() -> None:
    assert palette_for(Appearance.DARK) is DARK
    assert palette_for(Appearance.LIGHT) is LIGHT
