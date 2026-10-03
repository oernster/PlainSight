"""The import as a use case: ask GitHub, plan, write, say where it went."""

from __future__ import annotations

import os

import pytest

from plainsight.application.release_import import (
    CollectionWriteFailed,
    ImportCancelled,
    ImportStage,
    NetworkUnavailable,
    NoPublishedReleases,
    RateLimited,
    ReleaseImportService,
)
from plainsight.domain.release import Release
from plainsight.domain.repository_address import RepositoryAddress
from tests.application.release_fakes import FakeCollectionStore, FakeReleaseSource

ADDRESS = RepositoryAddress("oernster", "PlainSight")
OLDER = Release(source_id=1, tag="v1.0", published_at="2026-01-01T00:00:00Z")
NEWER = Release(source_id=2, tag="v2.0", published_at="2026-06-01T00:00:00Z")


def never() -> bool:
    return False


class Heard:
    """Records every stage reported, in order."""

    def __init__(self) -> None:
        self.stages: list[tuple[ImportStage, int]] = []

    def __call__(self, stage: ImportStage, count: int) -> None:
        self.stages.append((stage, count))


def service_with(
    source: FakeReleaseSource, store: FakeCollectionStore | None = None
) -> tuple[ReleaseImportService, FakeCollectionStore]:
    held = store if store is not None else FakeCollectionStore()
    return ReleaseImportService(source=source, store=held), held


def test_a_first_import_writes_every_release_and_names_the_newest() -> None:
    service, store = service_with(FakeReleaseSource((OLDER, NEWER)))

    outcome = service.import_releases(ADDRESS, Heard(), never)

    assert outcome.root == store.where
    assert outcome.newest == os.path.join(store.where, "2026-06-01_v2.0.md")
    assert not outcome.refreshed
    assert set(store.files) == {"2026-01-01_v1.0.md", "2026-06-01_v2.0.md"}


def test_the_stages_are_reported_in_order_with_their_counts() -> None:
    heard = Heard()
    service, _store = service_with(FakeReleaseSource((OLDER, NEWER)))

    service.import_releases(ADDRESS, heard, never)

    assert heard.stages == [
        (ImportStage.RETRIEVING, 0),
        (ImportStage.RETRIEVING, 2),
        (ImportStage.WRITING, 2),
    ]


def test_importing_again_refreshes_rather_than_duplicating() -> None:
    service, store = service_with(FakeReleaseSource((OLDER, NEWER)))
    service.import_releases(ADDRESS, Heard(), never)

    outcome = service.import_releases(ADDRESS, Heard(), never)

    assert outcome.refreshed
    assert outcome.plan.writes == ()
    assert len(store.files) == len((OLDER, NEWER))


def test_no_releases_is_reported_and_nothing_is_written() -> None:
    service, store = service_with(FakeReleaseSource(()))

    with pytest.raises(NoPublishedReleases):
        service.import_releases(ADDRESS, Heard(), never)

    assert store.commits == []


@pytest.mark.parametrize("problem", [NetworkUnavailable(), RateLimited(1)])
def test_a_problem_asking_github_writes_nothing(problem: Exception) -> None:
    service, store = service_with(FakeReleaseSource(problem=problem))

    with pytest.raises(type(problem)):
        service.import_releases(ADDRESS, Heard(), never)

    assert store.commits == []


def test_a_stop_before_writing_writes_nothing() -> None:
    service, store = service_with(FakeReleaseSource((OLDER,)))

    with pytest.raises(ImportCancelled):
        service.import_releases(ADDRESS, Heard(), lambda: True)

    assert store.commits == []


def test_a_failed_write_is_raised_as_the_problem_it_is() -> None:
    store = FakeCollectionStore()
    store.fail_commit = True
    service, _store = service_with(FakeReleaseSource((OLDER,)), store)

    with pytest.raises(CollectionWriteFailed):
        service.import_releases(ADDRESS, Heard(), never)


def test_a_rate_limit_carries_when_it_resets() -> None:
    assert RateLimited(1234).reset_epoch == 1234
    assert RateLimited().reset_epoch is None


def test_a_new_release_avoids_a_file_already_in_the_folder() -> None:
    """A file of the reader's under a release's natural name is left alone."""
    store = FakeCollectionStore()
    store.files["2026-06-01_v2.0.md"] = "the reader's own"
    service, _ = service_with(FakeReleaseSource((OLDER, NEWER)), store)

    outcome = service.import_releases(ADDRESS, Heard(), never)

    assert store.files["2026-06-01_v2.0.md"] == "the reader's own"
    assert outcome.plan.kept_edited == ()
    assert len(outcome.plan.added) == 2
    assert "2026-06-01_v2.0.md" not in outcome.plan.added
