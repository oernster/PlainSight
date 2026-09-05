"""The composition root: everything is wired here and nowhere else."""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from . import version
from .application.services import LibraryService
from .application.update import UpdateService, platform_key_for
from .infrastructure.desktop import DesktopEditorLauncher, QtExternalOpener
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


def build_service() -> LibraryService:
    """Every dependency, constructed once and injected."""
    return LibraryService(
        repository=FileSystemDocumentRepository(),
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
