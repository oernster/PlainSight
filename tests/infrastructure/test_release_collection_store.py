"""The collection on disk: built whole, refreshed safely, kept inside its folder."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from plainsight.application.release_import import CollectionWriteFailed
from plainsight.domain.release import Release
from plainsight.domain.release_collection import (
    FileWrite,
    RefreshPlan,
    ReleaseCollection,
    digest_of,
    file_names_for,
    plan_refresh,
)
from plainsight.domain.repository_address import RepositoryAddress
from plainsight.infrastructure import atomic_write, release_collection_store
from plainsight.infrastructure.collection_manifest import MANIFEST_NAME, render
from plainsight.infrastructure.release_collection_store import (
    UNREADABLE,
    FileSystemReleaseCollections,
)

ADDRESS = RepositoryAddress("oernster", "PlainSight")
ONE = Release(source_id=1, tag="v1", published_at="2026-01-01T00:00:00Z", body="a")
TWO = Release(source_id=2, tag="v2", published_at="2026-02-01T00:00:00Z", body="b")


def plan_for(store: FileSystemReleaseCollections, *releases: Release) -> RefreshPlan:
    """The plan the service would make against what the store holds now."""
    existing = store.load(ADDRESS)
    names = file_names_for(existing, releases)
    on_disk = store.digests(ADDRESS, tuple(names.values()))
    return plan_refresh(ADDRESS, existing, releases, names, on_disk)


@pytest.fixture
def store(tmp_path: Path) -> FileSystemReleaseCollections:
    return FileSystemReleaseCollections(tmp_path / "imports")


def folder(store: FileSystemReleaseCollections) -> Path:
    return Path(store.location(ADDRESS))


def test_the_folder_is_the_repository_beneath_its_owner(
    store: FileSystemReleaseCollections, tmp_path: Path
) -> None:
    assert folder(store) == tmp_path / "imports" / "oernster" / "PlainSight"


def test_a_first_import_creates_the_files_and_the_record(
    store: FileSystemReleaseCollections,
) -> None:
    assert store.load(ADDRESS) is None

    store.commit(ADDRESS, plan_for(store, ONE, TWO))

    names = sorted(path.name for path in folder(store).iterdir())
    assert names == [MANIFEST_NAME, "2026-01-01_v1.md", "2026-02-01_v2.md"]
    loaded = store.load(ADDRESS)
    assert loaded is not None
    assert loaded.file_names == ("2026-02-01_v2.md", "2026-01-01_v1.md")


def test_nothing_is_left_behind_in_staging(
    store: FileSystemReleaseCollections,
) -> None:
    store.commit(ADDRESS, plan_for(store, ONE))

    assert [path.name for path in folder(store).parent.iterdir()] == ["PlainSight"]


def test_a_failed_first_import_leaves_no_collection(
    store: FileSystemReleaseCollections, monkeypatch: pytest.MonkeyPatch
) -> None:
    def refuse(*_args: object) -> None:
        raise OSError("disk full")

    monkeypatch.setattr(release_collection_store.os, "rename", refuse)

    with pytest.raises(CollectionWriteFailed):
        store.commit(ADDRESS, plan_for(store, ONE, TWO))

    assert not folder(store).exists()
    assert list(folder(store).parent.iterdir()) == []


def test_a_failed_refresh_leaves_the_collection_readable(
    store: FileSystemReleaseCollections, monkeypatch: pytest.MonkeyPatch
) -> None:
    store.commit(ADDRESS, plan_for(store, ONE, TWO))
    before = {path.name: path.read_bytes() for path in folder(store).iterdir()}
    changed = (
        Release(source_id=1, tag="v1", published_at=ONE.published_at, body="new a"),
        Release(source_id=2, tag="v2", published_at=TWO.published_at, body="new b"),
    )
    plan = plan_for(store, *changed)
    real_replace = os.replace
    replaced: list[str] = []

    def replace_once(source: str, target: object) -> None:
        if replaced:
            raise OSError("the second write fails")
        replaced.append(str(target))
        real_replace(source, target)

    monkeypatch.setattr(atomic_write.os, "replace", replace_once)

    with pytest.raises(CollectionWriteFailed):
        store.commit(ADDRESS, plan)

    after = {path.name: path.read_bytes() for path in folder(store).iterdir()}
    assert set(after) == set(before)
    expected = {write.file_name: write.text.encode() for write in plan.writes}
    for name, content in after.items():
        assert content in (before[name], expected.get(name, before[name]))
    # And the next refresh recognises the file already replaced for what it is.
    monkeypatch.undo()
    again = plan_for(store, *changed)
    assert again.kept_edited == ()


def test_a_refresh_rewrites_only_what_it_was_told_to(
    store: FileSystemReleaseCollections,
) -> None:
    store.commit(ADDRESS, plan_for(store, ONE, TWO))
    untouched = folder(store) / "2026-01-01_v1.md"
    stamp = untouched.stat().st_mtime_ns
    changed = Release(source_id=2, tag="v2", published_at=TWO.published_at, body="c")

    plan = plan_for(store, ONE, changed)
    store.commit(ADDRESS, plan)

    assert plan.updated == ("2026-02-01_v2.md",)
    assert untouched.stat().st_mtime_ns == stamp
    assert "c" in (folder(store) / "2026-02-01_v2.md").read_text(encoding="utf-8")


def test_a_locally_edited_file_survives_a_refresh(
    store: FileSystemReleaseCollections,
) -> None:
    store.commit(ADDRESS, plan_for(store, ONE))
    edited = folder(store) / "2026-01-01_v1.md"
    edited.write_text("my own notes", encoding="utf-8")
    changed = Release(source_id=1, tag="v1", published_at=ONE.published_at, body="z")

    plan = plan_for(store, changed)
    store.commit(ADDRESS, plan)

    assert plan.kept_edited == ("2026-01-01_v1.md",)
    assert edited.read_text(encoding="utf-8") == "my own notes"


def test_a_name_that_climbs_out_is_refused(
    store: FileSystemReleaseCollections, tmp_path: Path
) -> None:
    store.commit(ADDRESS, plan_for(store, ONE))
    hostile = RefreshPlan(
        collection=ReleaseCollection(ADDRESS),
        writes=(FileWrite("../../escaped.md", "x"),),
    )

    with pytest.raises(CollectionWriteFailed):
        store.commit(ADDRESS, hostile)
    with pytest.raises(CollectionWriteFailed):
        store.digests(ADDRESS, ("..\\escaped.md",))

    assert not any(tmp_path.rglob("escaped.md"))


def test_a_tampered_record_cannot_name_a_file_outside(
    store: FileSystemReleaseCollections, tmp_path: Path
) -> None:
    store.commit(ADDRESS, plan_for(store, ONE))
    record = folder(store) / MANIFEST_NAME
    record.write_text(
        record.read_text(encoding="utf-8").replace(
            "2026-01-01_v1.md", "../../../escaped.md"
        ),
        encoding="utf-8",
    )

    store.commit(ADDRESS, plan_for(store, ONE))

    assert not any(tmp_path.rglob("escaped.md"))


def test_a_folder_with_an_unreadable_record_holds_the_readers_files(
    store: FileSystemReleaseCollections,
) -> None:
    store.commit(ADDRESS, plan_for(store, ONE))
    (folder(store) / MANIFEST_NAME).write_bytes(b"\xff\xfe not a record")

    assert store.load(ADDRESS) == ReleaseCollection(ADDRESS)


def test_a_record_for_another_repository_is_not_believed(
    store: FileSystemReleaseCollections,
) -> None:
    store.commit(ADDRESS, plan_for(store, ONE))
    elsewhere = ReleaseCollection(RepositoryAddress("someone", "Else"))
    (folder(store) / MANIFEST_NAME).write_text(render(elsewhere), encoding="utf-8")

    assert store.load(ADDRESS) == ReleaseCollection(ADDRESS)


def test_the_same_repository_spelled_in_another_case_is_the_same_folder(
    store: FileSystemReleaseCollections,
) -> None:
    store.commit(ADDRESS, plan_for(store, ONE))

    shouted = RepositoryAddress("OERNSTER", "plainsight")

    assert Path(store.location(shouted)) == folder(store)


def test_digests_answer_absent_readable_and_unreadable_files(
    store: FileSystemReleaseCollections,
) -> None:
    store.commit(ADDRESS, plan_for(store, ONE))
    (folder(store) / "2026-09-09_dir.md").mkdir()

    found = store.digests(
        ADDRESS, ("2026-01-01_v1.md", "2026-05-05_gone.md", "2026-09-09_dir.md")
    )

    written = (folder(store) / "2026-01-01_v1.md").read_text(encoding="utf-8")
    assert found == {
        "2026-01-01_v1.md": digest_of(written),
        "2026-05-05_gone.md": None,
        "2026-09-09_dir.md": UNREADABLE,
    }
