"""The tree filter: remembered, on until the reader turns it off, then applied.

The service owns the choice and tells the repository on every folder read, so
the tree the reader sees can never disagree with the setting that was saved.
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
    a_document,
    a_folder,
)

AN_EDITOR = EditorChoice(path="/usr/bin/vi", display_name="vi")
FILTER_OFF = Settings(documents_root="/notes", filter_tree=False)


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


def test_the_tree_filter_starts_on() -> None:
    assert a_service().tree_filtered() is True


def test_loading_asks_the_repository_to_filter_the_tree() -> None:
    repository = FakeRepository()
    store = FakeSettingsStore(Settings(documents_root="/notes"))

    a_service(repository=repository, store=store).load()

    assert repository.filter_asked == [True]


def test_loading_asks_for_everything_once_the_filter_is_off() -> None:
    repository = FakeRepository()

    a_service(repository=repository, store=FakeSettingsStore(FILTER_OFF)).load()

    assert repository.filter_asked == [False]


def test_choosing_a_root_carries_the_remembered_filter_into_the_read() -> None:
    repository = FakeRepository()
    store = FakeSettingsStore(Settings(filter_tree=False))

    a_service(repository=repository, store=store).choose_root("/chosen")

    assert repository.filter_asked == [False]


def test_turning_the_filter_off_remembers_it_and_reads_the_library_again() -> None:
    repository = FakeRepository({"/notes": a_folder("notes", "/notes")})
    store = FakeSettingsStore(Settings(documents_root="/notes"))
    service = a_service(repository=repository, store=store)

    library = service.filter_tree(False)

    assert store.settings.filter_tree is False
    assert service.tree_filtered() is False
    assert repository.filter_asked == [False]
    assert [root.name for root in library.roots] == ["notes"]


def test_turning_it_back_on_asks_the_repository_to_filter() -> None:
    repository = FakeRepository()
    store = FakeSettingsStore(FILTER_OFF)

    a_service(repository=repository, store=store).filter_tree(True)

    assert store.settings.filter_tree is True
    assert repository.filter_asked == [True]


def test_changing_the_filter_with_no_folder_chosen_reads_nothing() -> None:
    """Remembered all the same; nobody has authorised reading anything yet."""
    repository = FakeRepository()
    store = FakeSettingsStore()

    library = a_service(repository=repository, store=store).filter_tree(False)

    assert store.settings.filter_tree is False
    assert repository.roots_read == []
    assert library.is_empty


def test_changing_the_filter_keeps_everything_else_remembered() -> None:
    store = FakeSettingsStore(
        Settings(documents_root="/notes", editor=AN_EDITOR, opened_folders=("/a",))
    )

    a_service(store=store).filter_tree(False)

    assert store.settings.documents_root == "/notes"
    assert store.settings.editor == AN_EDITOR
    assert store.settings.opened_folders == ("/a",)


def test_one_file_opened_on_its_own_is_never_filtered() -> None:
    """Opening a file named that file; no folder is walked, so none is filtered."""
    document = a_document("empty.md", "/elsewhere")
    repository = FakeRepository(documents={document.path: document})

    library = a_service(repository=repository).open_file(document.path)

    assert repository.filter_asked == []
    assert [one.name for one in library] == ["empty.md"]
