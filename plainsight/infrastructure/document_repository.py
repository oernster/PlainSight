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
"""

from __future__ import annotations

from pathlib import Path

from ..domain.document import Document, DocumentKind, kind_of
from ..domain.library import Folder
from ..domain.parsing import EMPTY_FIELDS, ParsedDocument, parse_document

HIDDEN_PREFIX = "."
IGNORED_DIRECTORY_NAMES = frozenset({"__pycache__"})
UNREADABLE_TEXT = "This file could not be read as text."
MISSING_TEXT = "This file could not be opened."
EMPTY_TEXT = "This file holds no text."
EMPTY_MARKDOWN_TEXT = "This file holds no text beneath its frontmatter."


class FileSystemDocumentRepository:
    """Reads the documents held beneath a directory on this machine."""

    def read_folder(self, root: str) -> Folder | None:
        """``root`` as a tree; None when it is not a folder or holds nothing."""
        base = Path(root)
        if not base.is_dir():
            return None
        return self._folder(base, base.name or str(base))

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
                documents.append(_document(entry, kind))
        if not folders and not documents:
            return None
        return Folder.of(name, str(directory), folders, documents)


def _document(path: Path, kind: DocumentKind) -> Document:
    """One document read from this file, reporting a read that failed."""
    text, failure = _read_text(path)
    parsed = _parse(text, kind)
    if not failure and not parsed.body.strip():
        failure = EMPTY_MARKDOWN_TEXT if kind.declares_fields else EMPTY_TEXT
    return Document(
        name=path.name,
        path=str(path),
        kind=kind,
        body=parsed.body,
        declared_name=parsed.name,
        description=parsed.description,
        failure=failure,
        declared_fields=tuple(parsed.frontmatter.items()),
    )


def _parse(text: str, kind: DocumentKind) -> ParsedDocument:
    """The text split into fields and body, where this kind declares fields."""
    if kind.declares_fields:
        return parse_document(text)
    return ParsedDocument(frontmatter=EMPTY_FIELDS, body=text)


def _read_text(path: Path) -> tuple[str, str]:
    """The file's text with no failure; else empty text with a reason."""
    try:
        return path.read_text(encoding="utf-8"), ""
    except UnicodeDecodeError:
        return "", UNREADABLE_TEXT
    except OSError:
        return "", MISSING_TEXT


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
