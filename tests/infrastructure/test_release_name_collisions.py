"""A reader's own file never swallows a release that arrives later.

Imported files become the reader's the moment they exist; the reader may
add files of their own beside them. A new release whose natural name is already
taken on disk gets another name, so its notes are written and nothing of the
reader's is touched.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from plainsight.application.release_import import ReleaseImportService
from plainsight.domain.release import Release
from plainsight.domain.repository_address import RepositoryAddress
from plainsight.infrastructure.collection_manifest import MANIFEST_NAME
from plainsight.infrastructure.release_collection_store import (
    FileSystemReleaseCollections,
)

ADDRESS = RepositoryAddress("acme", "bar")
ONE = Release(source_id=1, tag="v1", published_at="2026-01-01T00:00:00Z", body="one")
TWO = Release(
    source_id=2, tag="v2", published_at="2026-02-01T00:00:00Z", body="REAL v2 NOTES"
)
TWOS_NATURAL_NAME = "2026-02-01_v2.md"
READERS_OWN = "MY OWN NOTES about what v2 should be"


class FixedSource:
    """Answers with the releases it was given, in that order."""

    def __init__(self, *releases: Release) -> None:
        self._releases = releases

    def releases(self, address: object, report: object, cancelled: object) -> tuple:
        return self._releases


def import_releases(store: FileSystemReleaseCollections, *releases: Release):
    service = ReleaseImportService(FixedSource(*releases), store)
    return service.import_releases(ADDRESS, lambda *_: None, lambda: False)


@pytest.fixture
def store(tmp_path: Path) -> FileSystemReleaseCollections:
    return FileSystemReleaseCollections(tmp_path / "imports")


@pytest.mark.parametrize("spelling", (TWOS_NATURAL_NAME, TWOS_NATURAL_NAME.upper()))
def test_a_release_named_like_the_readers_own_file_is_still_imported(
    store: FileSystemReleaseCollections, spelling: str
) -> None:
    import_releases(store, ONE)
    folder = Path(store.location(ADDRESS))
    mine = folder / spelling
    mine.write_text(READERS_OWN, encoding="utf-8")

    outcome = import_releases(store, ONE, TWO)

    assert mine.read_text(encoding="utf-8") == READERS_OWN
    assert outcome.plan.kept_edited == ()
    added = outcome.plan.added
    assert len(added) == 1
    assert added[0].casefold() != TWOS_NATURAL_NAME.casefold()
    assert "REAL v2 NOTES" in (folder / added[0]).read_text(encoding="utf-8")


def test_the_renamed_release_stays_where_it_was_put(
    store: FileSystemReleaseCollections,
) -> None:
    import_releases(store, ONE)
    folder = Path(store.location(ADDRESS))
    (folder / TWOS_NATURAL_NAME).write_text(READERS_OWN, encoding="utf-8")
    first = import_releases(store, ONE, TWO)

    again = import_releases(store, ONE, TWO)

    assert again.plan.added == ()
    assert again.plan.kept_edited == ()
    assert set(again.plan.unchanged) == {"2026-01-01_v1.md", first.plan.added[0]}
    assert (folder / TWOS_NATURAL_NAME).read_text(encoding="utf-8") == READERS_OWN


def test_a_folder_not_yet_made_holds_nothing(
    store: FileSystemReleaseCollections,
) -> None:
    assert store.present(ADDRESS) == ()


def test_every_file_in_the_folder_is_present(
    store: FileSystemReleaseCollections,
) -> None:
    import_releases(store, ONE)

    assert set(store.present(ADDRESS)) == {"2026-01-01_v1.md", MANIFEST_NAME}
