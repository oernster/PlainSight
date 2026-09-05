"""What the service remembers between runs: a look, a size, a place, a tag.

Separated from the reading tests because none of these touch a repository at
all: they are the settings the application carries from one run to the next,
each read back through the service that owns them.
"""

from __future__ import annotations

from plainsight.application.services import LibraryService
from plainsight.domain.settings import Appearance, EditorChoice, FontSize, Settings

from .fakes import (
    FakeLauncher,
    FakeOpener,
    FakePaths,
    FakeProbe,
    FakeRepository,
    FakeSettingsStore,
)

AN_EDITOR = EditorChoice(path="/usr/bin/vi", display_name="vi")


def a_service(store: FakeSettingsStore | None = None) -> LibraryService:
    return LibraryService(
        repository=FakeRepository(),
        settings_store=store if store is not None else FakeSettingsStore(),
        launcher=FakeLauncher(),
        opener=FakeOpener(),
        probe=FakeProbe(),
        paths=FakePaths(),
    )


def test_the_appearance_starts_dark() -> None:
    assert a_service().appearance() is Appearance.DARK


def test_switching_remembers_the_other_appearance_and_reports_it() -> None:
    store = FakeSettingsStore()
    service = a_service(store=store)

    assert service.switch_appearance() is Appearance.LIGHT
    assert store.settings.appearance is Appearance.LIGHT
    assert service.appearance() is Appearance.LIGHT


def test_switching_twice_returns_to_where_it_started() -> None:
    service = a_service(store=FakeSettingsStore())

    service.switch_appearance()

    assert service.switch_appearance() is Appearance.DARK


def test_a_fresh_install_has_every_folder_shut() -> None:
    assert a_service().opened_folders() == ()


def test_the_folders_a_reader_opens_are_remembered() -> None:
    store = FakeSettingsStore()
    service = a_service(store=store)

    service.remember_opened_folders(("/skills/prose",))

    assert service.opened_folders() == ("/skills/prose",)
    assert store.settings.opened_folders == ("/skills/prose",)


def test_nothing_is_skipped_until_something_is() -> None:
    assert a_service().skipped_update_version() == ""


def test_a_skipped_release_is_remembered() -> None:
    store = FakeSettingsStore()
    service = a_service(store=store)

    service.skip_update_version("0.2.0")

    assert service.skipped_update_version() == "0.2.0"
    assert store.settings.skipped_update_version == "0.2.0"


def test_skipping_a_release_keeps_everything_else_remembered() -> None:
    store = FakeSettingsStore(Settings(documents_root="/skills", editor=AN_EDITOR))
    service = a_service(store=store)

    service.skip_update_version("0.2.0")

    assert store.settings.documents_root == "/skills"
    assert store.settings.editor == AN_EDITOR


def test_text_starts_at_the_middle_size() -> None:
    assert a_service().font_size() is FontSize.MEDIUM


def test_cycling_the_text_size_steps_it_and_remembers_it() -> None:
    store = FakeSettingsStore()
    service = a_service(store=store)

    assert service.cycle_font_size() is FontSize.LARGE
    assert store.settings.font_size is FontSize.LARGE
    assert service.font_size() is FontSize.LARGE


def test_cycling_past_the_largest_returns_to_the_smallest() -> None:
    service = a_service(
        store=FakeSettingsStore(Settings(font_size=FontSize.EXTRA_LARGE))
    )

    assert service.cycle_font_size() is FontSize.MEDIUM


def test_cycling_the_text_size_keeps_everything_else_remembered() -> None:
    store = FakeSettingsStore(Settings(documents_root="/skills", editor=AN_EDITOR))
    service = a_service(store=store)

    service.cycle_font_size()

    assert store.settings.documents_root == "/skills"
    assert store.settings.editor == AN_EDITOR
