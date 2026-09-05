"""Opening one document, which must not become a look at its neighbours."""

from __future__ import annotations

import os

from plainsight.application.services import LibraryService
from plainsight.domain.settings import Settings

from .fakes import (
    FakeLauncher,
    FakeOpener,
    FakePaths,
    FakeProbe,
    FakeRepository,
    FakeSettingsStore,
    a_document,
)

A_FOLDER = os.path.join("home", "notes")
A_PATH = os.path.join(A_FOLDER, "shopping.txt")


def a_service(
    repository: FakeRepository, store: FakeSettingsStore | None = None
) -> LibraryService:
    return LibraryService(
        repository=repository,
        settings_store=store if store is not None else FakeSettingsStore(),
        launcher=FakeLauncher(),
        opener=FakeOpener(),
        probe=FakeProbe(),
        paths=FakePaths(),
    )


def a_repository() -> FakeRepository:
    return FakeRepository(documents={A_PATH: a_document("shopping.txt", A_FOLDER)})


def test_one_file_arrives_as_a_library_of_one() -> None:
    library = a_service(a_repository()).open_file(A_PATH)

    assert library.document_count == 1
    assert [one.name for one in library] == ["shopping.txt"]


def test_the_folder_row_is_named_from_the_path_rather_than_listed() -> None:
    """The reader is shown where it came from without anything being scanned."""
    repository = a_repository()

    library = a_service(repository).open_file(A_PATH)

    assert [root.name for root in library.roots] == ["notes"]
    assert repository.roots_read == []
    assert repository.files_read == [A_PATH]


def test_a_file_of_a_kind_we_do_not_read_gives_an_empty_library() -> None:
    """Reported to the reader rather than shown as a folder holding nothing."""
    library = a_service(FakeRepository()).open_file(os.path.join(A_FOLDER, "photo.png"))

    assert library.is_empty


def test_opening_a_file_does_not_change_the_remembered_folder() -> None:
    """A look in passing: the next run opens on the folder that was chosen."""
    store = FakeSettingsStore(Settings(documents_root="/chosen"))

    a_service(a_repository(), store).open_file(A_PATH)

    assert store.settings.documents_root == "/chosen"
    assert store.saved == []


def test_a_file_at_the_root_of_a_drive_still_names_its_holder() -> None:
    """`basename` of a drive root is empty, so the path itself has to stand in."""
    root_path = os.path.join(os.sep, "notes.md")
    repository = FakeRepository(
        documents={root_path: a_document("notes.md", os.sep.rstrip(os.sep))}
    )

    library = a_service(repository).open_file(root_path)

    assert len(library.roots) == 1
    assert library.roots[0].name
