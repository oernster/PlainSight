"""A repository's imported releases as a folder; how a refresh changes it.

Everything a refresh decides is decided here, as a plan, before a byte is
written: which files are new, which changed on GitHub, which the reader edited
and which releases GitHub no longer lists. Writing the plan is somebody else's
job. Deciding it apart from the writing is what makes the rule that nothing the
reader wrote is lost a table of cases rather than a hope.

A file is known by digest. The digest recorded is of what was last written, so
a file whose digest has moved since was changed by somebody other than the
importer. That is the reader; their version is kept.
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from .file_names import release_file_stem, unique_name
from .release import Release, release_markdown
from .repository_address import RepositoryAddress

ENCODING = "utf-8"


def digest_of_bytes(data: bytes) -> str:
    """A fingerprint of these bytes, long enough that two files never share one."""
    return hashlib.sha256(data).hexdigest()


def digest_of(text: str) -> str:
    """The fingerprint of ``text`` as it is written to disk."""
    return digest_of_bytes(text.encode(ENCODING))


@dataclass(frozen=True, slots=True)
class CollectionEntry:
    """One release's file: which release, when it was, what was last written."""

    source_id: int
    tag: str
    published_at: str
    file_name: str
    digest: str

    @property
    def chronology(self) -> tuple[int, str, int, str]:
        """Newest first when sorted ascending; undated last; then newest id.

        GitHub numbers releases as they are made, so between two carrying the
        same moment the higher number is the later one. The tag settles the
        rest, which only a malformed record could need.
        """
        dated = 0 if self.published_at else 1
        return (dated, _descending(self.published_at), -self.source_id, self.tag)


@dataclass(frozen=True, slots=True)
class ReleaseCollection:
    """What a folder of imported releases holds, newest first."""

    address: RepositoryAddress
    entries: tuple[CollectionEntry, ...] = ()

    @staticmethod
    def of(
        address: RepositoryAddress, entries: Iterable[CollectionEntry]
    ) -> ReleaseCollection:
        """A collection with its entries in display order."""
        ordered = sorted(entries, key=lambda entry: entry.chronology)
        return ReleaseCollection(address=address, entries=tuple(ordered))

    def entry_for(self, source_id: int) -> CollectionEntry | None:
        """The entry for this release; None when the collection has none."""
        for entry in self.entries:
            if entry.source_id == source_id:
                return entry
        return None

    @property
    def file_names(self) -> tuple[str, ...]:
        """Every file the collection holds, newest first."""
        return tuple(entry.file_name for entry in self.entries)


@dataclass(frozen=True, slots=True)
class FileWrite:
    """One file to write, whole, with the text it is to hold."""

    file_name: str
    text: str


@dataclass(frozen=True, slots=True)
class RefreshPlan:
    """Everything a refresh will do, decided before any of it is done."""

    collection: ReleaseCollection
    writes: tuple[FileWrite, ...] = ()
    added: tuple[str, ...] = ()
    updated: tuple[str, ...] = ()
    unchanged: tuple[str, ...] = ()
    kept_edited: tuple[str, ...] = ()
    kept_withdrawn: tuple[str, ...] = ()


def file_names_for(
    existing: ReleaseCollection | None,
    releases: Iterable[Release],
    present: Iterable[str] = (),
) -> dict[int, str]:
    """The file each release lives in: the one it had, else a new unique one.

    A release keeps its file by its GitHub number, so a retagged or retitled
    release is the same file rather than a second one. New releases are named
    oldest number first, so the same set of releases always gets the same
    names whatever order GitHub listed them in.

    ``present`` is every file in the folder now. A new name avoids those too:
    a file the reader put there under a release's natural name is theirs; the
    release it collides with is written beside it rather than lost to it.
    """
    known = {} if existing is None else _names_by_id(existing)
    taken = {name.casefold() for name in (*known.values(), *present)}
    names = dict(known)
    fresh = sorted(
        (one for one in releases if one.source_id not in known),
        key=lambda one: one.source_id,
    )
    for release in fresh:
        stem = release_file_stem(release.published_at, release.tag)
        names[release.source_id] = unique_name(stem, taken)
    return names


def plan_refresh(
    address: RepositoryAddress,
    existing: ReleaseCollection | None,
    releases: Iterable[Release],
    names: Mapping[int, str],
    on_disk: Mapping[str, str | None],
) -> RefreshPlan:
    """What to write so the folder holds GitHub's releases, losing nothing.

    ``on_disk`` is the digest of each named file as it stands now; None where
    there is no such file. A file already holding what would be written is left
    alone, which also mends a refresh that was interrupted after some files had
    been replaced.
    """
    previous = existing if existing is not None else ReleaseCollection(address)
    entries: list[CollectionEntry] = []
    writes: list[FileWrite] = []
    outcome: dict[str, list[str]] = {
        key: [] for key in ("added", "updated", "unchanged", "kept_edited")
    }
    seen: set[int] = set()
    for release in releases:
        seen.add(release.source_id)
        name = names[release.source_id]
        text = release_markdown(release)
        wanted = digest_of(text)
        recorded = previous.entry_for(release.source_id)
        current = on_disk.get(name)
        kept = recorded.digest if recorded is not None else ""
        if current is None or (recorded is not None and current == recorded.digest):
            if current != wanted:
                writes.append(FileWrite(name, text))
                outcome["added" if current is None else "updated"].append(name)
            else:
                outcome["unchanged"].append(name)
            kept = wanted
        elif current == wanted:
            outcome["unchanged"].append(name)
            kept = wanted
        else:
            outcome["kept_edited"].append(name)
        entries.append(_entry(release, name, kept))
    withdrawn = [
        entry
        for entry in previous.entries
        if entry.source_id not in seen and on_disk.get(entry.file_name) is not None
    ]
    entries.extend(withdrawn)
    return RefreshPlan(
        collection=ReleaseCollection.of(address, entries),
        writes=tuple(writes),
        added=tuple(outcome["added"]),
        updated=tuple(outcome["updated"]),
        unchanged=tuple(outcome["unchanged"]),
        kept_edited=tuple(outcome["kept_edited"]),
        kept_withdrawn=tuple(entry.file_name for entry in withdrawn),
    )


def _entry(release: Release, file_name: str, digest: str) -> CollectionEntry:
    """The record of one release as it now stands in the folder."""
    return CollectionEntry(
        source_id=release.source_id,
        tag=release.tag,
        published_at=release.published_at,
        file_name=file_name,
        digest=digest,
    )


def _names_by_id(collection: ReleaseCollection) -> dict[int, str]:
    """Each recorded release's file, by its GitHub number."""
    return {entry.source_id: entry.file_name for entry in collection.entries}


def _descending(moment: str) -> tuple[int, ...]:
    """A moment as a key that sorts later moments first.

    Every moment has the one fixed form, so negating each character's code
    point reverses the order text comparison would give.
    """
    return tuple(-ord(character) for character in moment)
