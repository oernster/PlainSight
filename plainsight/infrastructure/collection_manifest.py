"""The record a collection keeps of itself, as the JSON file it is stored in.

One file, hidden, in the collection's own folder: where its documents came
from and which document is which, in the order they are shown. The order is
the only part the tree reads, which is why it is stated generically as a list
of documents rather than as anything to do with releases: a folder declaring
an order is a folder declaring an order, whoever wrote it.

The file is somebody's to edit like any other, so everything read back from it
is checked before it is believed. A record that cannot be read is treated as
no record, which makes every file in the folder the reader's own.
"""

from __future__ import annotations

import json

from ..domain.file_names import is_safe_file_name
from ..domain.release import MOMENT_PATTERN
from ..domain.release_collection import CollectionEntry, ReleaseCollection
from ..domain.repository_address import InvalidRepositoryAddress, RepositoryAddress

MANIFEST_NAME = ".plainsight-collection.json"
FORMAT_VERSION = 1
INDENT = 2

FORMAT_KEY = "format"
SOURCE_KEY = "source"
KIND_KEY = "kind"
OWNER_KEY = "owner"
REPOSITORY_KEY = "repository"
URL_KEY = "url"
DOCUMENTS_KEY = "documents"
FILE_KEY = "file"
RELEASE_ID_KEY = "release_id"
TAG_KEY = "tag"
PUBLISHED_KEY = "published_at"
DIGEST_KEY = "digest"

GITHUB_RELEASES = "github-releases"


def render(collection: ReleaseCollection) -> str:
    """The record as the text written to disk, documents in display order."""
    address = collection.address
    payload = {
        FORMAT_KEY: FORMAT_VERSION,
        SOURCE_KEY: {
            KIND_KEY: GITHUB_RELEASES,
            OWNER_KEY: address.owner,
            REPOSITORY_KEY: address.name,
            URL_KEY: address.web_url,
        },
        DOCUMENTS_KEY: [
            {
                FILE_KEY: entry.file_name,
                RELEASE_ID_KEY: entry.source_id,
                TAG_KEY: entry.tag,
                PUBLISHED_KEY: entry.published_at,
                DIGEST_KEY: entry.digest,
            }
            for entry in collection.entries
        ],
    }
    return json.dumps(payload, indent=INDENT, ensure_ascii=False) + "\n"


def declared_order(text: str) -> tuple[str, ...]:
    """The file names a record lists, in its order; none from a bad record.

    The names are only compared with names already found in the folder, never
    opened, so nothing more than their being strings is asked of them.
    """
    documents = _documents(_payload(text))
    names = (one.get(FILE_KEY) for one in documents if isinstance(one, dict))
    return tuple(name for name in names if isinstance(name, str))


def parse(text: str) -> ReleaseCollection | None:
    """The collection a record describes; None when it describes none.

    An entry that fails any check is left out rather than failing the record,
    so the file it named is treated as the reader's own and is never written
    over on its say-so. A name or a release claimed twice keeps its first
    claim for the same reason.
    """
    payload = _payload(text)
    if payload.get(FORMAT_KEY) != FORMAT_VERSION:
        return None
    address = _address(payload.get(SOURCE_KEY))
    if address is None:
        return None
    entries: list[CollectionEntry] = []
    names: set[str] = set()
    ids: set[int] = set()
    for raw in _documents(payload):
        entry = _entry(raw)
        if entry is None:
            continue
        if entry.file_name.casefold() in names or entry.source_id in ids:
            continue
        names.add(entry.file_name.casefold())
        ids.add(entry.source_id)
        entries.append(entry)
    return ReleaseCollection.of(address, entries)


def _payload(text: str) -> dict:
    """The decoded record; an empty one when it is not a JSON object."""
    try:
        payload = json.loads(text)
    except ValueError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _documents(payload: dict) -> list:
    """The record's document list; an empty one when it holds no list."""
    documents = payload.get(DOCUMENTS_KEY)
    return documents if isinstance(documents, list) else []


def _address(source: object) -> RepositoryAddress | None:
    """The repository a record says it came from; None when it names none."""
    if not isinstance(source, dict) or source.get(KIND_KEY) != GITHUB_RELEASES:
        return None
    owner = source.get(OWNER_KEY)
    name = source.get(REPOSITORY_KEY)
    if not isinstance(owner, str) or not isinstance(name, str):
        return None
    try:
        return RepositoryAddress(owner=owner, name=name)
    except InvalidRepositoryAddress:
        return None


def _entry(raw: object) -> CollectionEntry | None:
    """One document's record; None when any part of it cannot be believed."""
    if not isinstance(raw, dict):
        return None
    file_name = raw.get(FILE_KEY)
    source_id = raw.get(RELEASE_ID_KEY)
    tag = raw.get(TAG_KEY)
    published = raw.get(PUBLISHED_KEY)
    digest = raw.get(DIGEST_KEY)
    if not isinstance(file_name, str) or not is_safe_file_name(file_name):
        return None
    if not isinstance(source_id, int) or isinstance(source_id, bool):
        return None
    if not isinstance(tag, str) or not isinstance(digest, str):
        return None
    if not isinstance(published, str):
        return None
    if published and not MOMENT_PATTERN.fullmatch(published):
        return None
    return CollectionEntry(
        source_id=source_id,
        tag=tag,
        published_at=published,
        file_name=file_name,
        digest=digest,
    )
