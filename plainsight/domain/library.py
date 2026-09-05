"""The folders and documents beneath the roots being read, as a tree.

The tree mirrors the directories on disk rather than gathering everything into
one list. A folder of notes is a folder of notes; a skill is a folder holding
its ``SKILL.md`` and whatever else travels with it, which is the same shape
said the same way.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from dataclasses import dataclass

from .document import Document


@dataclass(frozen=True, slots=True)
class Folder:
    """One directory: the folders inside it, then the documents it holds.

    Folders come before documents and each group is ordered case insensitively
    by name, which is the one ordering rule the application has. Build through
    ``of`` rather than the constructor, so nothing has to remember to sort.
    """

    name: str
    path: str
    folders: tuple[Folder, ...] = ()
    documents: tuple[Document, ...] = ()

    @staticmethod
    def of(
        name: str,
        path: str,
        folders: Iterable[Folder] = (),
        documents: Iterable[Document] = (),
    ) -> Folder:
        """A folder with its contents in display order."""
        return Folder(
            name=name,
            path=path,
            folders=tuple(sorted(folders, key=lambda folder: folder.sort_key)),
            documents=tuple(sorted(documents, key=lambda one: one.sort_key)),
        )

    @property
    def sort_key(self) -> str:
        """The key a parent orders its folders by: the name, case folded."""
        return self.name.casefold()

    @property
    def document_count(self) -> int:
        """Every document beneath this folder, however deep."""
        return len(self.documents) + sum(
            folder.document_count for folder in self.folders
        )

    @property
    def is_empty(self) -> bool:
        """Whether this folder leads to no document at any depth."""
        return self.document_count == 0

    def __iter__(self) -> Iterator[Document]:
        """Every document beneath this folder, in the order they are drawn.

        Folders are drawn above documents, so a folder's own documents come
        after everything its subfolders hold. Walking in drawing order is what
        lets a caller reason about the list the reader is actually looking at.
        """
        for folder in self.folders:
            yield from folder
        yield from self.documents


@dataclass(frozen=True, slots=True)
class Library:
    """The roots being read, in the order they are shown.

    There are usually two: the folder the reader chose and the plugins tree
    that sits beside it. A root that holds no documents is not carried at all,
    so an empty library is genuinely empty rather than a heading over nothing.
    """

    roots: tuple[Folder, ...] = ()

    @property
    def is_empty(self) -> bool:
        """Whether the roots between them hold no documents at all."""
        return all(root.is_empty for root in self.roots)

    @property
    def document_count(self) -> int:
        """Every document in every root."""
        return sum(root.document_count for root in self.roots)

    def by_path(self, path: str) -> Document | None:
        """The document read from this path; None when there is no such one."""
        for document in self:
            if document.path == path:
                return document
        return None

    def __iter__(self) -> Iterator[Document]:
        """Every document in the library, in the order they are drawn."""
        for root in self.roots:
            yield from root
