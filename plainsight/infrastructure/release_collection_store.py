"""Imported releases kept as a folder of Markdown files, one per repository.

Each repository has its own folder beneath its owner's, so two owners with a
repository of the same name can never share one. Every name in the path is
made safe before it is used and every file is checked to land inside its
collection before it is written, whoever supplied the name.

Writing obeys the rule the whole import is built on: what was usable before
stays usable after, whatever fails. A first import is built in a hidden
staging folder and moved into place only once complete, so a failure leaves
nothing at all rather than half a history. A refresh replaces each file whole,
the record last; a failure partway leaves every file either as it was or as it
was meant to become. The next refresh recognises the second kind for what it
is.

This is one of the two modules in the application allowed to write, together
with the settings store; it writes nowhere but beneath its own root.
"""

from __future__ import annotations

import os
import shutil
import tempfile
import time
from collections.abc import Callable
from pathlib import Path

from ..application.release_import import CollectionWriteFailed
from ..domain.file_names import is_safe_file_name, safe_segment
from ..domain.release_collection import (
    ENCODING,
    RefreshPlan,
    ReleaseCollection,
    digest_of_bytes,
)
from ..domain.repository_address import RepositoryAddress
from .atomic_write import write_atomically
from .collection_manifest import MANIFEST_NAME, parse, render

STAGING_PREFIX = ".staging-"
# A staging folder lives only while a first import writes its files, which is
# well under a second. One untouched for this long belongs to an import that
# died before it could clean up. The margin keeps the sweep from reaching one
# that another running copy of the application is writing into right now.
STALE_STAGING_SECONDS = 10 * 60
# Stands for a file that is there and cannot be read. It is no digest, so it
# matches nothing and the file is treated as the reader's own and left alone.
UNREADABLE = "unreadable"
CLIMBS_OUT = "Refused a file name that would land outside the collection: {!r}"


class FileSystemReleaseCollections:
    """Collections held on this machine beneath one root directory."""

    def __init__(self, root: Path, clock: Callable[[], float] | None = None) -> None:
        self._root = root
        # Injected so a test can age a staging folder without waiting.
        self._clock = time.time if clock is None else clock

    def location(self, address: RepositoryAddress) -> str:
        """The folder this repository's releases live in, there or not."""
        return str(self._directory(address))

    def load(self, address: RepositoryAddress) -> ReleaseCollection | None:
        """What the folder records; None when there is no folder yet."""
        directory = self._directory(address)
        if not directory.is_dir():
            return None
        try:
            text = (directory / MANIFEST_NAME).read_text(encoding=ENCODING)
        except (OSError, UnicodeDecodeError):
            return ReleaseCollection(address)
        found = parse(text)
        if found is None or not found.address.same_repository(address):
            return ReleaseCollection(address)
        return ReleaseCollection.of(address, found.entries)

    def digests(
        self, address: RepositoryAddress, file_names: tuple[str, ...]
    ) -> dict[str, str | None]:
        """Each named file's digest as it stands; None where it is absent."""
        directory = self._directory(address)
        found: dict[str, str | None] = {}
        for name in file_names:
            path = _inside(directory, name)
            try:
                found[name] = digest_of_bytes(path.read_bytes())
            except FileNotFoundError:
                found[name] = None
            except OSError:
                found[name] = UNREADABLE
        return found

    def commit(self, address: RepositoryAddress, plan: RefreshPlan) -> None:
        """Carry out the plan whole; raises ``CollectionWriteFailed`` otherwise."""
        directory = self._directory(address)
        _sweep_stale_staging(directory.parent, self._clock())
        try:
            if directory.is_dir():
                _refresh(directory, plan)
            else:
                _create(directory, plan)
        except OSError as error:
            raise CollectionWriteFailed(str(error)) from error

    def _directory(self, address: RepositoryAddress) -> Path:
        """``root/owner/repository``, reusing a folder differing only in case.

        GitHub ignores case in both names, so ``oernster/plainsight`` and
        ``oernster/PlainSight`` are one repository and must be one folder even
        on a file system that would happily hold two.
        """
        owner = _existing(self._root, safe_segment(address.owner))
        return _existing(owner, safe_segment(address.name))


def _create(directory: Path, plan: RefreshPlan) -> None:
    """Build the whole collection out of sight, then move it into place."""
    directory.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=STAGING_PREFIX, dir=directory.parent))
    try:
        for write in plan.writes:
            _inside(staging, write.file_name).write_bytes(write.text.encode(ENCODING))
        (staging / MANIFEST_NAME).write_bytes(_record(plan))
        os.rename(staging, directory)
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def _sweep_stale_staging(owner: Path, now: float) -> None:
    """Remove staging folders a dead import left beside this owner's collections.

    Only a directory directly in the owner's folder, named with the staging
    prefix and untouched for ``STALE_STAGING_SECONDS``, is removed. A link is
    never followed, whatever it is called. Anything that cannot be looked at or
    removed is left where it is: a sweep that fails costs a hidden folder,
    never the import it runs ahead of.
    """
    try:
        entries = list(owner.iterdir())
    except OSError:
        return
    for entry in entries:
        if not entry.name.startswith(STAGING_PREFIX) or entry.is_symlink():
            continue
        try:
            stale = now - entry.stat().st_mtime > STALE_STAGING_SECONDS
        except OSError:
            continue
        if stale and entry.is_dir():
            shutil.rmtree(entry, ignore_errors=True)


def _refresh(directory: Path, plan: RefreshPlan) -> None:
    """Replace each file whole, then the record that describes them."""
    for write in plan.writes:
        write_atomically(
            _inside(directory, write.file_name), write.text.encode(ENCODING)
        )
    write_atomically(directory / MANIFEST_NAME, _record(plan))


def _record(plan: RefreshPlan) -> bytes:
    """The collection's record as the bytes written."""
    return render(plan.collection).encode(ENCODING)


def _inside(directory: Path, name: str) -> Path:
    """The path of a release file in this folder; refused if it would leave it.

    The name has to be one ``file_names`` could have made, which already rules
    out a separator, a device name and a name made of dots; the parent is then
    checked as well, since this is the last point before a byte is written.
    """
    path = directory / name
    if not is_safe_file_name(name) or path.parent != directory:
        raise CollectionWriteFailed(CLIMBS_OUT.format(name))
    return path


def _existing(parent: Path, name: str) -> Path:
    """``parent / name``; else a folder already there differing only in case."""
    wanted = parent / name
    if wanted.exists() or not parent.is_dir():
        return wanted
    folded = name.casefold()
    try:
        entries = list(parent.iterdir())
    except OSError:
        return wanted
    for entry in entries:
        if entry.name.casefold() == folded and entry.is_dir():
            return entry
    return wanted
