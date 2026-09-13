"""Whether ``venv`` and ``node_modules`` are read: remembered, then applied.

The service owns the choice and tells the repository on every read, so the tree
the reader sees can never disagree with the setting that was saved.
"""

from __future__ import annotations

from plainsight.application.services import LibraryService
from plainsight.domain.settings import EditorChoice, Settings

from .fakes import (
    FakeLauncher,
    FakeOpener,
    FakePaths,
    FakeProbe,
    FakeRepository,
    FakeSettingsStore,
    a_folder,
)

AN_EDITOR = EditorChoice(path="/usr/bin/vi", display_name="vi")


def a_service(
    repository: FakeRepository | None = None, store: FakeSettingsStore | None = None
) -> LibraryService:
    return LibraryService(
        repository=repository if repository is not None else FakeRepository(),
        settings_store=store if store is not None else FakeSettingsStore(),
        launcher=FakeLauncher(),
        opener=FakeOpener(),
        probe=FakeProbe(),
        paths=FakePaths(),
    )


def test_environment_folders_start_hidden() -> None:
    assert a_service().environment_folders_shown() is False


def test_loading_asks_the_repository_to_pass_environment_folders_over() -> None:
    repository = FakeRepository()
    store = FakeSettingsStore(Settings(documents_root="/notes"))

    a_service(repository=repository, store=store).load()

    assert repository.environment_folders_asked == [False]


def test_loading_asks_for_them_once_the_reader_has_chosen_to_see_them() -> None:
    repository = FakeRepository()
    store = FakeSettingsStore(
        Settings(documents_root="/notes", show_environment_folders=True)
    )

    a_service(repository=repository, store=store).load()

    assert repository.environment_folders_asked == [True]


def test_choosing_a_root_carries_the_remembered_choice_into_the_read() -> None:
    repository = FakeRepository()
    store = FakeSettingsStore(Settings(show_environment_folders=True))

    a_service(repository=repository, store=store).choose_root("/chosen")

    assert repository.environment_folders_asked == [True]


def test_showing_them_remembers_it_and_reads_the_library_again() -> None:
    repository = FakeRepository({"/notes": a_folder("notes", "/notes")})
    store = FakeSettingsStore(Settings(documents_root="/notes"))
    service = a_service(repository=repository, store=store)

    library = service.show_environment_folders(True)

    assert store.settings.show_environment_folders is True
    assert service.environment_folders_shown() is True
    assert repository.environment_folders_asked == [True]
    assert [root.name for root in library.roots] == ["notes"]


def test_hiding_them_again_asks_the_repository_to_pass_them_over() -> None:
    repository = FakeRepository()
    store = FakeSettingsStore(
        Settings(documents_root="/notes", show_environment_folders=True)
    )

    a_service(repository=repository, store=store).show_environment_folders(False)

    assert store.settings.show_environment_folders is False
    assert repository.environment_folders_asked == [False]


def test_changing_the_choice_with_no_folder_chosen_reads_nothing() -> None:
    """Remembered all the same; nobody has authorised reading anything yet."""
    repository = FakeRepository()
    store = FakeSettingsStore()

    library = a_service(repository=repository, store=store).show_environment_folders(
        True
    )

    assert store.settings.show_environment_folders is True
    assert repository.roots_read == []
    assert library.is_empty


def test_changing_the_choice_keeps_everything_else_remembered() -> None:
    store = FakeSettingsStore(
        Settings(documents_root="/notes", editor=AN_EDITOR, opened_folders=("/a",))
    )

    a_service(store=store).show_environment_folders(True)

    assert store.settings.documents_root == "/notes"
    assert store.settings.editor == AN_EDITOR
    assert store.settings.opened_folders == ("/a",)
