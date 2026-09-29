"""The collection's own record: written, read back, never simply believed."""

from __future__ import annotations

import json

import pytest

from plainsight.domain.release_collection import CollectionEntry, ReleaseCollection
from plainsight.domain.repository_address import RepositoryAddress
from plainsight.infrastructure.collection_manifest import (
    declared_order,
    parse,
    render,
)

ADDRESS = RepositoryAddress("oernster", "PlainSight")
NEWER = CollectionEntry(2, "v2", "2026-06-01T00:00:00Z", "2026-06-01_v2.md", "b")
OLDER = CollectionEntry(1, "v1", "2026-01-01T00:00:00Z", "2026-01-01_v1.md", "a")
COLLECTION = ReleaseCollection.of(ADDRESS, [OLDER, NEWER])


def record(**changes: object) -> str:
    payload = json.loads(render(COLLECTION))
    payload.update(changes)
    return json.dumps(payload)


def with_document(**changes: object) -> str:
    payload = json.loads(render(COLLECTION))
    payload["documents"][0].update(changes)
    return json.dumps(payload)


def test_a_record_reads_back_as_the_collection_it_was() -> None:
    assert parse(render(COLLECTION)) == COLLECTION


def test_the_record_names_its_source_and_lists_documents_newest_first() -> None:
    payload = json.loads(render(COLLECTION))

    assert payload["source"]["url"] == "https://github.com/oernster/PlainSight"
    assert [one["file"] for one in payload["documents"]] == [
        "2026-06-01_v2.md",
        "2026-01-01_v1.md",
    ]


def test_the_declared_order_is_the_document_list() -> None:
    assert declared_order(render(COLLECTION)) == (
        "2026-06-01_v2.md",
        "2026-01-01_v1.md",
    )


@pytest.mark.parametrize("text", ["", "[]", "{", '{"documents": 5}'])
def test_a_record_that_cannot_be_read_declares_no_order(text: str) -> None:
    assert declared_order(text) == ()


def test_an_order_keeps_only_the_names_that_are_text() -> None:
    text = json.dumps({"documents": [{"file": "a.md"}, {"file": 3}, "b.md"]})

    assert declared_order(text) == ("a.md",)


@pytest.mark.parametrize(
    "text",
    [
        "not json",
        record(format=2),
        record(source="github"),
        record(source={"kind": "elsewhere", "owner": "o", "repository": "r"}),
        record(source={"kind": "github-releases", "owner": 1, "repository": "r"}),
        record(source={"kind": "github-releases", "owner": "o", "repository": ".."}),
    ],
)
def test_a_record_describing_no_collection_is_none(text: str) -> None:
    assert parse(text) is None


@pytest.mark.parametrize(
    "changes",
    [
        {"file": "../../escape.md"},
        {"file": "notes.txt"},
        {"file": None},
        {"release_id": "2"},
        {"release_id": True},
        {"tag": None},
        {"digest": 5},
        {"published_at": None},
        {"published_at": "last week"},
    ],
)
def test_an_entry_that_cannot_be_believed_is_left_out(
    changes: dict[str, object],
) -> None:
    parsed = parse(with_document(**changes))

    assert parsed is not None
    assert parsed.entries == (OLDER,)


def test_an_entry_that_is_not_an_object_is_left_out() -> None:
    payload = json.loads(render(COLLECTION))
    payload["documents"].insert(0, "stray")

    assert parse(json.dumps(payload)) == COLLECTION


def test_a_file_or_a_release_claimed_twice_keeps_its_first_claim() -> None:
    payload = json.loads(render(COLLECTION))
    first = dict(payload["documents"][0])
    payload["documents"].append(dict(first, release_id=99))
    payload["documents"].append(dict(first, file="other.md"))

    parsed = parse(json.dumps(payload))

    assert parsed == COLLECTION


def test_an_undated_entry_is_believed() -> None:
    undated = CollectionEntry(3, "v3", "", "undated_v3.md", "c")

    parsed = parse(render(ReleaseCollection.of(ADDRESS, [undated])))

    assert parsed is not None and parsed.entries == (undated,)
