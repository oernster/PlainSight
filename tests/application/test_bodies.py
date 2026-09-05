"""When a document's text is read; when it is deliberately not.

A library holds every document beneath the folder that was chosen. Holding
every body with it meant reading every file to show one of them, which was
free while the kinds were Markdown and text and stops being free for a kind
that has to be extracted rather than decoded.
"""

from __future__ import annotations

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
    a_folder,
)

A_ROOT = "/chosen"
NOTHING_READ = 0


def a_service(repository: FakeRepository) -> LibraryService:
    """A service reading the chosen root, with everything else a stand in."""
    return LibraryService(
        repository=repository,
        settings_store=FakeSettingsStore(Settings(documents_root=A_ROOT)),
        launcher=FakeLauncher(),
        opener=FakeOpener(),
        probe=FakeProbe(),
        paths=FakePaths(),
    )


def test_reading_the_library_reads_no_bodies() -> None:
    """The whole point of the seam, said as the assertion it is."""
    repository = FakeRepository({A_ROOT: a_folder("chosen", A_ROOT, "a.md", "b.md")})

    library = a_service(repository).load()

    assert library.document_count == 2
    assert len(repository.bodies_read) == NOTHING_READ


def test_opening_a_document_reads_its_body_and_only_its_body() -> None:
    document = a_document("a.md", A_ROOT)
    repository = FakeRepository(bodies={document.path: "The text."})

    body = a_service(repository).body_of(document)

    assert body.text == "The text."
    assert not body.failure
    assert repository.bodies_read == [document.path]


def test_a_body_that_cannot_be_read_now_comes_back_empty() -> None:
    """A file moved between being listed and being opened is not a crash."""
    document = a_document("gone.md", A_ROOT)

    assert a_service(FakeRepository()).body_of(document).text == ""
