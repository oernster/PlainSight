"""What is being read: a folder the reader chose, else one file they opened.

The two are one concern rather than two, because a re-read has to know which it
is looking at. The library is read again every time the window is activated,
which is the whole freshness model and has no watcher and no polling thread
behind it. Closing a chooser is what activates the window, so a re-read that
always went back to the chosen folder threw away a file the moment it was
opened: the file was read, shown, then replaced before the reader saw it.

Holding both the choice and the re-read here is what stops those two answers
being given in different places and disagreeing.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from ..domain.library import Library
from . import dialogs
from .library_tree import DOCUMENT_ROLE, FIRST_COLUMN

if TYPE_CHECKING:  # pragma: no cover
    # For the annotation only. The window builds this, so importing it at
    # runtime would close a circle.
    from .main_window import MainWindow


class ReadingChoice:
    """Which documents are on screen; how to read them again."""

    def __init__(self, window: MainWindow) -> None:
        self._window = window
        self._is_empty = True
        self._opened_file: str | None = None

    @property
    def is_empty(self) -> bool:
        """Whether what is being read holds no documents at all.

        Distinct from having chosen nothing, which the window asks the service
        about: a folder that was read and held nothing is not the same fact as
        a machine that has not been read at all.
        """
        return self._is_empty

    def refresh(self) -> None:
        """Read what is being shown again and show what it holds now.

        A single opened file is re-read as itself rather than replaced by the
        chosen folder. Both are the same promise: what is on screen is what is
        on disk now.
        """
        self._show(self._again())

    def filter_tree(self, on: bool) -> None:
        """Remember whether the tree is filtered; show the tree again.

        The tree keeps the folders the reader left open, as any re-read does.
        A single opened file is re-read as itself, since the filter is about
        walking folders and one file walks none.
        """
        library = self._window.service.filter_tree(on)
        if self._opened_file is None:
            self._show(library)
        else:
            self.refresh()

    def choose_folder(self) -> None:
        """Browse to a folder of documents and read it.

        The chooser opens on the last folder taken, else on the user's home
        directory. That is a starting place for a
        dialog the user is standing in front of; nothing is read until they
        take something.
        """
        service = self._window.service
        chosen = dialogs.ask_for_folder(self._window, service.browse_from())
        if not chosen:
            return
        # Choosing a folder is the reader saying they want the folder, so a
        # file opened before this stops being what is read.
        self._opened_file = None
        self._show(service.choose_root(chosen))

    def open_file(self) -> None:
        """Open one document, listing no directory around it.

        Selected as soon as it is read, which is not the auto-selection the
        tree refuses: a reader who names one file has already chosen it, where
        a reader who names a folder has not chosen anything inside it.
        """
        service = self._window.service
        chosen = dialogs.ask_for_document(self._window, service.browse_from())
        if not chosen:
            return
        library = service.open_file(chosen)
        if library.is_empty:
            self._window.report_status(self._window.unreadable_file_message)
            return
        self._opened_file = chosen
        self._show(library, only_document=True)

    def open_collection(self, root: str, newest: str) -> None:
        """Read an imported folder as the folder chosen; land on ``newest``.

        Chosen exactly as a folder picked in the chooser is, so it is
        remembered and re-read like one. Landing on its newest document is not
        the auto-selection the tree refuses: the reader asked for these
        release notes by importing them, so the newest is what they came for.
        """
        self._opened_file = None
        self._show(self._window.service.choose_root(root))
        self._select_path(newest)

    def _again(self) -> Library:
        """The library as it stands now: the opened file, else the folder.

        A file that has gone since it was opened falls back to the folder
        rather than leaving the reader looking at a tree that describes
        nothing.
        """
        service = self._window.service
        if self._opened_file is None:
            return service.load()
        library = service.open_file(self._opened_file)
        if not library.is_empty:
            return library
        self._opened_file = None
        return service.load()

    def _show(self, library: Library, only_document: bool = False) -> None:
        """Put this library on screen and land the reader where they belong."""
        self._is_empty = library.is_empty
        tree = self._window.library_tree
        tree.show_library(library)
        if only_document:
            self._select_the_only_document()
        else:
            self._window.show_document(tree.selected_document())

    def _select_the_only_document(self) -> None:
        """Open the one folder there is and land on the document inside it."""
        tree = self._window.library_tree
        for item in tree.folder_items():
            item.setExpanded(True)
        rows = tree.document_items()
        if rows:
            tree.setCurrentItem(rows[0])

    def _select_path(self, path: str) -> None:
        """Open the folders above the document read from ``path``; select it."""
        tree = self._window.library_tree
        for item in tree.document_items():
            if not same_path(item.data(FIRST_COLUMN, DOCUMENT_ROLE).path, path):
                continue
            parent = item.parent()
            while parent is not None:
                parent.setExpanded(True)
                parent = parent.parent()
            tree.setCurrentItem(item)
            return


def same_path(first: str, second: str) -> bool:
    """Whether two paths name one file, however each was spelled."""
    return os.path.normcase(os.path.normpath(first)) == os.path.normcase(
        os.path.normpath(second)
    )
