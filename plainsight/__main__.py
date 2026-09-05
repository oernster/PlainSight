"""The composition root: everything is wired here and nowhere else."""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from . import version
from .application.ports import DocumentReader
from .application.services import LibraryService
from .application.update import UpdateService, platform_key_for
from .domain.document import DocumentKind
from .infrastructure.desktop import DesktopEditorLauncher, QtExternalOpener
from .infrastructure.document_reader import TextDocumentReader
from .infrastructure.document_repository import FileSystemDocumentRepository
from .infrastructure.platform import (
    FileSystemPathProbe,
    HomePlatformPaths,
    settings_path,
)
from .infrastructure.renderer import DocumentHtmlRenderer
from .infrastructure.resources import BundledAssets
from .infrastructure.settings_store import JsonSettingsStore
from .infrastructure.update_source import GitHubReleaseSource
from .ui.main_window import MainWindow


def build_readers() -> dict[DocumentKind, DocumentReader]:
    """One reader per kind, named here rather than worked out anywhere else.

    Written out rather than derived from the enumeration, so a kind added
    without a reader is a gap somebody has to fill on purpose instead of one
    silently filled with the wrong reader. A structural test holds this to
    covering every kind there is.
    """
    return {
        DocumentKind.MARKDOWN: TextDocumentReader(DocumentKind.MARKDOWN),
        DocumentKind.PLAIN_TEXT: TextDocumentReader(DocumentKind.PLAIN_TEXT),
        DocumentKind.HTML: TextDocumentReader(DocumentKind.HTML),
    }


def build_service() -> LibraryService:
    """Every dependency, constructed once and injected."""
    return LibraryService(
        repository=FileSystemDocumentRepository(build_readers()),
        settings_store=JsonSettingsStore(settings_path()),
        launcher=DesktopEditorLauncher(),
        opener=QtExternalOpener(),
        probe=FileSystemPathProbe(),
        paths=HomePlatformPaths(),
    )


def build_update_service() -> UpdateService:
    """The update check, told which release file this machine can run."""
    return UpdateService(
        source=GitHubReleaseSource(),
        current_version=version.__version__,
        platform_key=platform_key_for(sys.platform),
    )


def main() -> int:
    """Start the application."""
    application = QApplication(sys.argv)
    window = MainWindow(
        build_service(),
        DocumentHtmlRenderer(),
        BundledAssets(),
        build_update_service(),
    )
    window.present()
    return application.exec()


if __name__ == "__main__":
    raise SystemExit(main())
