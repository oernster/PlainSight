"""The composition root: everything is wired here and nowhere else."""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from .application.services import SkillLibraryService
from .infrastructure.desktop import DesktopEditorLauncher, QtExternalOpener
from .infrastructure.markdown_renderer import PythonMarkdownRenderer
from .infrastructure.platform import (
    FileSystemPathProbe,
    HomePlatformPaths,
    settings_path,
)
from .infrastructure.resources import BundledAssets
from .infrastructure.settings_store import JsonSettingsStore
from .infrastructure.skill_repository import FileSystemSkillRepository
from .ui.main_window import MainWindow
from .ui.theme import DARK, stylesheet


def build_service() -> SkillLibraryService:
    """Every dependency, constructed once and injected."""
    return SkillLibraryService(
        repository=FileSystemSkillRepository(),
        settings_store=JsonSettingsStore(settings_path()),
        launcher=DesktopEditorLauncher(),
        opener=QtExternalOpener(),
        probe=FileSystemPathProbe(),
        paths=HomePlatformPaths(),
    )


def main() -> int:
    """Start the application."""
    application = QApplication(sys.argv)
    application.setStyleSheet(stylesheet(DARK))
    window = MainWindow(
        build_service(), PythonMarkdownRenderer(), BundledAssets(), DARK
    )
    window.show()
    return application.exec()


if __name__ == "__main__":
    raise SystemExit(main())
