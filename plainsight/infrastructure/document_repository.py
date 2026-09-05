"""Reads a directory tree and reports the documents in it, as a tree.

The rules are plain enough to state in a sentence: every file whose suffix
names a kind this application reads is a document; every directory holding
one at any depth is a folder; hidden and cache directories are passed over. A
folder leading to no document is not reported at all, so every branch the
reader can open leads somewhere.

Nothing here is specific to any one tool. A Claude skills folder reads as the
folders of skills it is, each holding its ``SKILL.md`` and whatever travels
with it; a folder of notes reads as the notes it holds. That is the same rule
applied to both rather than two rules that happen to agree.

Nor is anything here specific to any one kind of file. What a file of a given
kind says about itself is a reader's business; this walks the tree, decides
what is a document at all and says what each file was when it was listed.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from ..application.ports import DocumentReader
from ..domain.document import Document, DocumentBody, DocumentKind, kind_of
from ..domain.library import Folder

HIDDEN_PREFIX = "."
IGNORED_DIRECTORY_NAMES = frozenset({"__pycache__"})
UNKNOWN_KIND = "This file is not one this application reads."


class FileSystemDocumentRepository:
    """Reads the documents held beneath a directory on this machine."""

    def __init__(self, readers: Mapping[DocumentKind, DocumentReader]) -> None:
        self._readers = dict(readers)

    def read_folder(self, root: str) -> Folder | None:
        """``root`` as a tree; None when it is not a folder or holds nothing."""
        base = Path(root)
        if not base.is_dir():
            return None
        return self._folder(base, base.name or str(base))

    def read_document(self, path: str) -> Document | None:
        """One file, listing no directory; None when it is not one we read.

        Nothing here calls ``iterdir``. A reader who opened one file asked
        about that file, so the directory holding it is named from the path
        rather than looked into: whatever else sits beside it stays unread.
        """
        wanted = Path(path)
        kind = kind_of(wanted.name)
        if kind is None or not wanted.is_file():
            return None
        return self._document(wanted, kind)

    def read_body(self, path: str) -> DocumentBody:
        """The text of this file, read now, else why there is none.

        The body of a document is fetched when it is opened rather than kept
        from when it was listed. A library of two hundred documents held two
        hundred bodies to show one of them, which was free for Markdown and
        will not be for a kind that has to be extracted rather than decoded.
        """
        kind = kind_of(Path(path).name)
        if kind is None:
            return DocumentBody(failure=UNKNOWN_KIND)
        return self._readers[kind].read_body(path)

    def _folder(self, directory: Path, name: str) -> Folder | None:
        """This directory as a folder; None when nothing beneath it is read."""
        folders: list[Folder] = []
        documents: list[Document] = []
        for entry in _entries(directory):
            if entry.is_dir():
                if _is_ignored(entry.name):
                    continue
                child = self._folder(entry, entry.name)
                if child is not None:
                    folders.append(child)
                continue
            kind = kind_of(entry.name)
            if kind is not None:
                documents.append(self._document(entry, kind))
        if not folders and not documents:
            return None
        return Folder.of(name, str(directory), folders, documents)

    def _document(self, path: Path, kind: DocumentKind) -> Document:
        """One document as it was listed, its reader saying what it declares.

        The body is not among what is kept. What a listing needs is what a
        document says about itself, whether it can be read at all and what the
        file was at the time; the text itself is fetched when it is opened.
        """
        summary = self._readers[kind].summarise(str(path))
        return Document(
            name=path.name,
            path=str(path),
            kind=kind,
            fingerprint=_fingerprint(path),
            declared_name=summary.declared_name,
            description=summary.description,
            failure=summary.failure,
            declared_fields=summary.declared_fields,
        )


def _fingerprint(path: Path) -> str:
    """What this file is right now, said briefly enough to compare.

    Size and modification time together, which is one look at the directory
    entry rather than a read of the file. A document carries it so that the
    same file edited since compares as the different document it is, which is
    how the reading pane knows to draw it again rather than leave the reader
    where they were.

    A file that cannot be looked at fingerprints as nothing. That makes it
    compare equal to another unreadable one, which costs a redraw that shows
    the same failure message either way.
    """
    try:
        status = path.stat()
    except OSError:
        return ""
    return f"{status.st_size}:{status.st_mtime_ns}"


def _entries(directory: Path) -> list[Path]:
    """What this directory holds; nothing at all when it cannot be listed.

    A directory the account cannot open is passed over rather than raised on:
    one unreadable folder somewhere beneath a root must not cost the reader
    the whole tree.
    """
    try:
        return sorted(directory.iterdir(), key=lambda entry: entry.name.casefold())
    except OSError:
        return []


def _is_ignored(name: str) -> bool:
    """Whether a directory of this name is passed over rather than scanned."""
    return name.startswith(HIDDEN_PREFIX) or name in IGNORED_DIRECTORY_NAMES
