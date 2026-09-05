"""The application's own questions and commands, above the toolkit.

The service is frozen and holds only its injected dependencies. It answers
questions rather than holding the answers, so the user interface asks whether a
control should be enabled instead of working it out for itself.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from ..domain.document import Document
from ..domain.library import Folder, Library
from ..domain.settings import Appearance, EditorChoice, FontSize, Settings
from .defaults import browse_from, chosen_root, default_editor, plugins_root_for
from .ports import (
    DocumentRepository,
    EditorLauncher,
    ExternalOpener,
    PathProbe,
    PlatformPaths,
    SettingsStore,
)


@dataclass(frozen=True, slots=True)
class LibraryService:
    """Reads the library, remembers the choices and hands work outwards."""

    repository: DocumentRepository
    settings_store: SettingsStore
    launcher: EditorLauncher
    opener: ExternalOpener
    probe: PathProbe
    paths: PlatformPaths

    def current_root(self) -> str:
        """The folder the user chose; empty when they have chosen none."""
        return chosen_root(self.settings_store.load().documents_root)

    def has_root(self) -> bool:
        """Whether a folder has been chosen at all."""
        return bool(self.current_root())

    def browse_from(self) -> str:
        """Where the folder chooser opens; it reads nothing on its own."""
        return browse_from(self.settings_store.load().documents_root, self.paths)

    def load(self) -> Library:
        """Every document the chosen folder holds; nothing until one is chosen.

        A reader who has chosen no folder gets an empty library rather than a
        walk of their home directory. Reading somebody's files is theirs to
        authorise, so the application asks before it looks.
        """
        root = self.current_root()
        return self._read(root) if root else Library()

    def choose_root(self, root: str) -> Library:
        """Remember this root and read it."""
        settings = self.settings_store.load().with_root(root)
        self.settings_store.save(settings)
        return self._read(root)

    def open_file(self, path: str) -> Library:
        """One file on its own, shown under the folder that holds it.

        No directory is listed. The folder row is named from the path so the
        reader can see where the file came from; whatever else sits beside it
        stays unread, because opening one file asked about one file.

        The choice is deliberately not remembered. This is a look at something
        in passing, so the next run opens on the folder the reader chose rather
        than on whatever they last glanced at.
        """
        document = self.repository.read_document(path)
        if document is None:
            return Library()
        holder = os.path.dirname(os.path.normpath(path))
        name = os.path.basename(holder) or holder
        return Library((Folder.of(name, holder, documents=[document]),))

    def _read(self, root: str) -> Library:
        """The chosen folder, plus the plugins tree it implies where it does.

        The two are combined here rather than in the user interface, so what
        the library holds stays a property of the library rather than of the
        widget showing it. A tree that is not there contributes no root rather
        than an empty one; nor does one leading to no document at any depth.

        Only a Claude skills folder implies a sibling, so anywhere else exactly
        one directory is read: the one the user picked and no other.
        """
        plugins = plugins_root_for(root)
        wanted = (root, plugins) if plugins else (root,)
        found = tuple(self.repository.read_folder(one) for one in wanted)
        return Library(
            tuple(one for one in found if one is not None and not one.is_empty)
        )

    def choose_editor(self, editor: EditorChoice) -> None:
        """Remember the editor to launch documents in."""
        self.settings_store.save(self.settings_store.load().with_editor(editor))

    def opened_folders(self) -> tuple[str, ...]:
        """The folders the user has open; none at all until one is opened."""
        return self.settings_store.load().opened_folders

    def remember_opened_folders(self, opened: tuple[str, ...]) -> None:
        """Remember which folders are open, so a run opens as the last one closed."""
        self.settings_store.save(self.settings_store.load().with_opened_folders(opened))

    def skipped_update_version(self) -> str:
        """The release tag the user asked not to hear about again."""
        return self.settings_store.load().skipped_update_version

    def skip_update_version(self, tag: str) -> None:
        """Remember not to mention this release again."""
        self.settings_store.save(
            self.settings_store.load().with_skipped_update_version(tag)
        )

    def appearance(self) -> Appearance:
        """The palette the application should draw with now."""
        return self.settings_store.load().appearance

    def switch_appearance(self) -> Appearance:
        """Remember the other appearance; report which it now is."""
        wanted = self.settings_store.load().appearance.other
        self.settings_store.save(self.settings_store.load().with_appearance(wanted))
        return wanted

    def font_size(self) -> FontSize:
        """The size the application should draw its text at now."""
        return self.settings_store.load().font_size

    def cycle_font_size(self) -> FontSize:
        """Step to the next size and remember it; report which it now is."""
        wanted = self.settings_store.load().font_size.next_in_cycle
        self.settings_store.save(self.settings_store.load().with_font_size(wanted))
        return wanted

    def settings(self) -> Settings:
        """What is remembered right now."""
        return self.settings_store.load()

    def effective_editor(self) -> EditorChoice | None:
        """The editor to use: the one chosen, else the machine's own default."""
        chosen = self.settings_store.load().editor
        return chosen if chosen is not None else default_editor(self.paths, self.probe)

    def can_open_in_editor(self, document: Document | None) -> bool:
        """Whether the view in editor control has anything it could do.

        A document has to be selected, an editor has to have been chosen and
        that editor has to still be where it was when it was chosen; an editor
        uninstalled since is no longer a thing this can act on.
        """
        if document is None:
            return False
        editor = self.effective_editor()
        if editor is None:
            return False
        return self.probe.exists(editor.path)

    def open_in_editor(self, document: Document) -> bool:
        """Open this document in the chosen editor.

        False when there is no usable editor or the desktop declined to start
        it, which the caller reports rather than swallowing.
        """
        editor = self.effective_editor()
        if editor is None:
            return False
        return self.launcher.launch(editor, document.path)

    def open_page(self, address: str) -> bool:
        """Hand an address to the desktop; False when it declined.

        The application asks for nothing itself here: the address goes out and
        the browser does the fetching.
        """
        return self.opener.open(address)

    def open_donation_page(self, address: str) -> bool:
        """Hand the donation address to the desktop; False when it declined."""
        return self.open_page(address)
