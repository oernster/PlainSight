"""A refresh as a plan: added, updated, unchanged and never the reader's loss."""

from __future__ import annotations

from plainsight.domain.release import Release, release_markdown
from plainsight.domain.release_collection import (
    CollectionEntry,
    ReleaseCollection,
    digest_of,
    digest_of_bytes,
    file_names_for,
    plan_refresh,
)
from plainsight.domain.repository_address import RepositoryAddress

ADDRESS = RepositoryAddress("oernster", "PlainSight")
EDITED = digest_of("somebody's own words")


def a_release(source_id: int, day: str = "10", **changes: object) -> Release:
    fields: dict[str, object] = {
        "source_id": source_id,
        "tag": f"v1.{source_id}",
        "published_at": f"2026-09-{day}T12:00:00Z",
        "body": f"Notes for {source_id}\n",
    }
    fields.update(changes)
    return Release(**fields)  # type: ignore[arg-type]


def first_import(*releases: Release):
    names = file_names_for(None, releases)
    plan = plan_refresh(ADDRESS, None, releases, names, {})
    return names, plan


def disk_after(plan) -> dict[str, str | None]:
    """What the folder holds once a plan was written, by digest."""
    return {write.file_name: digest_of(write.text) for write in plan.writes}


def test_a_first_import_writes_every_release() -> None:
    releases = (a_release(1, "01"), a_release(2, "02"))

    _names, plan = first_import(*releases)

    assert [write.text for write in plan.writes] == [
        release_markdown(one) for one in releases
    ]
    assert plan.added == ("2026-09-01_v1.1.md", "2026-09-02_v1.2.md")
    assert plan.updated == plan.unchanged == plan.kept_edited == ()


def test_entries_are_newest_first_whatever_their_names() -> None:
    """Names that sort the wrong way by text still list newest first."""
    releases = (
        a_release(1, "05", tag="zzz-oldest"),
        a_release(2, "20", tag="aaa-newest"),
        a_release(3, "12", tag="mmm-middle"),
    )

    _names, plan = first_import(*releases)

    assert [entry.tag for entry in plan.collection.entries] == [
        "aaa-newest",
        "mmm-middle",
        "zzz-oldest",
    ]


def test_equal_dates_fall_to_the_newest_number_then_undated_come_last() -> None:
    releases = (
        a_release(4, "10"),
        a_release(9, "10"),
        a_release(12, published_at=""),
        a_release(2, published_at=""),
        a_release(1, "11"),
    )

    _names, plan = first_import(*releases)

    assert [entry.source_id for entry in plan.collection.entries] == [1, 9, 4, 12, 2]


def test_the_order_does_not_depend_on_the_order_github_listed_them_in() -> None:
    releases = [a_release(n, f"{n:02d}") for n in range(1, 9)]

    _forward, forwards = first_import(*releases)
    _backward, backwards = first_import(*reversed(releases))

    assert forwards.collection == backwards.collection


def test_the_same_releases_again_change_nothing() -> None:
    releases = (a_release(1), a_release(2, "11"))
    names, plan = first_import(*releases)

    again = plan_refresh(ADDRESS, plan.collection, releases, names, disk_after(plan))

    assert again.writes == ()
    assert set(again.unchanged) == set(names.values())
    assert again.collection == plan.collection


def test_a_known_release_keeps_its_file_name() -> None:
    """Retagged on GitHub, it is still the same file rather than a second one."""
    names, plan = first_import(a_release(1))
    retagged = a_release(1, tag="v1.1-final")

    renamed = file_names_for(plan.collection, (retagged,))

    assert renamed == names


def test_a_new_release_is_added_beside_the_rest() -> None:
    names, plan = first_import(a_release(1, "01"))
    releases = (a_release(1, "01"), a_release(2, "02"))
    names = file_names_for(plan.collection, releases)

    again = plan_refresh(ADDRESS, plan.collection, releases, names, disk_after(plan))

    assert again.added == ("2026-09-02_v1.2.md",)
    assert [write.file_name for write in again.writes] == ["2026-09-02_v1.2.md"]
    assert again.collection.file_names == ("2026-09-02_v1.2.md", "2026-09-01_v1.1.md")


def test_an_unedited_file_whose_release_changed_is_rewritten() -> None:
    names, plan = first_import(a_release(1))
    changed = (a_release(1, body="Corrected notes\n"),)

    again = plan_refresh(ADDRESS, plan.collection, changed, names, disk_after(plan))

    assert again.updated == (names[1],)
    assert again.writes[0].text == release_markdown(changed[0])
    assert again.collection.entries[0].digest == digest_of(again.writes[0].text)


def test_an_edited_file_is_kept_and_reported() -> None:
    names, plan = first_import(a_release(1))
    changed = (a_release(1, body="Corrected notes\n"),)

    again = plan_refresh(ADDRESS, plan.collection, changed, names, {names[1]: EDITED})

    assert again.writes == ()
    assert again.kept_edited == (names[1],)
    # The record still holds what was last written, so it stays the reader's.
    assert again.collection.entries[0].digest == plan.collection.entries[0].digest


def test_an_edited_file_whose_release_did_not_change_is_left_quietly() -> None:
    names, plan = first_import(a_release(1))

    again = plan_refresh(
        ADDRESS, plan.collection, (a_release(1),), names, {names[1]: EDITED}
    )

    assert again.writes == ()
    assert again.kept_edited == (names[1],)


def test_a_withdrawn_release_keeps_its_file() -> None:
    names, plan = first_import(a_release(1, "01"), a_release(2, "02"))

    again = plan_refresh(
        ADDRESS, plan.collection, (a_release(2, "02"),), names, disk_after(plan)
    )

    assert again.kept_withdrawn == (names[1],)
    assert again.collection.file_names == (names[2], names[1])
    assert again.writes == ()


def test_a_withdrawn_release_whose_file_is_gone_is_forgotten() -> None:
    names, plan = first_import(a_release(1, "01"), a_release(2, "02"))
    on_disk = {names[2]: disk_after(plan)[names[2]], names[1]: None}

    again = plan_refresh(
        ADDRESS, plan.collection, (a_release(2, "02"),), names, on_disk
    )

    assert again.kept_withdrawn == ()
    assert again.collection.file_names == (names[2],)


def test_a_deleted_file_of_a_published_release_is_written_again() -> None:
    names, plan = first_import(a_release(1))

    again = plan_refresh(ADDRESS, plan.collection, (a_release(1),), names, {})

    assert again.added == (names[1],)


def test_an_interrupted_refresh_is_recognised_rather_than_called_an_edit() -> None:
    """The file already holds the new text while the record still has the old."""
    names, plan = first_import(a_release(1))
    changed = (a_release(1, body="Corrected notes\n"),)
    already = {names[1]: digest_of(release_markdown(changed[0]))}

    again = plan_refresh(ADDRESS, plan.collection, changed, names, already)

    assert again.writes == ()
    assert again.unchanged == (names[1],)
    assert again.collection.entries[0].digest == already[names[1]]


def test_a_file_already_there_with_no_record_is_the_readers_own() -> None:
    """A lost record must not make the importer write over what it finds."""
    names = file_names_for(ReleaseCollection(ADDRESS), (a_release(1),))

    plan = plan_refresh(
        ADDRESS, ReleaseCollection(ADDRESS), (a_release(1),), names, {names[1]: EDITED}
    )

    assert plan.writes == ()
    assert plan.kept_edited == (names[1],)


def test_a_found_file_already_holding_the_text_is_adopted() -> None:
    names = file_names_for(None, (a_release(1),))
    same = {names[1]: digest_of(release_markdown(a_release(1)))}

    plan = plan_refresh(ADDRESS, None, (a_release(1),), names, same)

    assert plan.writes == ()
    assert plan.unchanged == (names[1],)


def test_an_entry_can_be_found_by_its_release_number() -> None:
    entry = CollectionEntry(1, "v1", "", "undated_v1.md", "d")
    collection = ReleaseCollection.of(ADDRESS, [entry])

    assert collection.entry_for(1) is entry
    assert collection.entry_for(2) is None


def test_the_digest_of_text_is_the_digest_of_its_bytes() -> None:
    assert digest_of("é") == digest_of_bytes("é".encode())


def test_a_new_name_avoids_every_file_present_whatever_its_case() -> None:
    names = file_names_for(None, (a_release(1),), ("2026-09-10_V1.1.MD",))

    assert names[1].casefold() != "2026-09-10_v1.1.md"
    assert names[1].endswith(".md")
