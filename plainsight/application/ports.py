"""The seams the application talks through. Infrastructure implements them."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from ..domain.document import DocumentKind
from ..domain.library import Folder
from ..domain.settings import EditorChoice, Settings

if TYPE_CHECKING:  # pragma: no cover
    # Imported for the annotation only. The release types live beside the
    # service that uses them, which imports this module, so a runtime import
    # here would close a circle.
    from .update import ReleaseInfo


class DocumentRepository(Protocol):
    """Reads a directory tree and reports the documents in it."""

    def read_folder(self, root: str) -> Folder | None:
        """``root`` as a tree; None when it is not a folder or holds nothing."""
        ...


class SettingsStore(Protocol):
    """Remembers the root and the editor between runs."""

    def load(self) -> Settings:
        """What was remembered; the defaults when nothing was."""
        ...

    def save(self, settings: Settings) -> None:
        """Remember this, replacing whatever was there."""
        ...


class EditorLauncher(Protocol):
    """Hands a file to the editor the user chose."""

    def launch(self, editor: EditorChoice, target: str) -> bool:
        """Open ``target`` in ``editor``; False when the desktop declined."""
        ...


class ExternalOpener(Protocol):
    """Hands an address to whatever the desktop opens links with."""

    def open(self, address: str) -> bool:
        """Ask for this address; False when the desktop declined."""
        ...


class PathProbe(Protocol):
    """Answers whether a path is there, without reading it."""

    def exists(self, path: str) -> bool:
        """Whether something exists at this path."""
        ...


class PlatformPaths(Protocol):
    """The few locations that differ per operating system."""

    def home_directory(self) -> str:
        """The current user's home directory."""
        ...

    def program_directories(self) -> tuple[str, ...]:
        """Where installed programs live; empty where that has no meaning."""
        ...

    def system_directory(self) -> str:
        """Where the operating system keeps its own programs; empty if none."""
        ...


class AssetLocator(Protocol):
    """Finds the artwork the build bundled, wherever it was packaged into."""

    def find(self, name: str) -> str | None:
        """The path of the bundled asset of this name; None when absent."""
        ...


class DocumentRenderer(Protocol):
    """Turns a document's body into something a reading surface can show."""

    def render(self, body: str, kind: DocumentKind) -> str:
        """The body as HTML, laid out as this kind of document asks."""
        ...


class ReleaseSource(Protocol):
    """Reports the latest published release of this application."""

    def latest_release(self) -> ReleaseInfo | None:
        """The newest release; None when the source could not be asked."""
        ...
