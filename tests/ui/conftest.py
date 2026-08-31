"""One real QApplication for the whole session; Qt is never mocked."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication, QWidget

from skillsviewer.application.services import SkillLibraryService
from skillsviewer.domain.settings import Settings
from skillsviewer.infrastructure.markdown_renderer import PythonMarkdownRenderer
from skillsviewer.infrastructure.resources import BundledAssets
from skillsviewer.infrastructure.skill_repository import FileSystemSkillRepository
from skillsviewer.ui.main_window import MainWindow
from tests.application.fakes import (
    FakeLauncher,
    FakeOpener,
    FakePaths,
    FakeProbe,
    FakeSettingsStore,
)

A_DOCUMENT = "---\nname: {name}\ndescription: about {name}\n---\n\n# {name}\n\nBody.\n"


@pytest.fixture(scope="session")
def application() -> Iterator[QApplication]:
    existing = QApplication.instance()
    app = existing if existing is not None else QApplication([])
    yield app


@pytest.fixture(autouse=True)
def close_orphans(application: QApplication) -> Iterator[None]:
    """Nothing left on screen between tests."""
    yield
    for widget in list(application.topLevelWidgets()):
        if isinstance(widget, QWidget):
            widget.close()


@pytest.fixture
def skills_root(tmp_path: Path) -> Path:
    root = tmp_path / "skills"
    for name in ("prose", "dev", "keeb"):
        directory = root / name
        directory.mkdir(parents=True)
        (directory / "SKILL.md").write_text(
            A_DOCUMENT.format(name=name), encoding="utf-8"
        )
    return root


@pytest.fixture
def store() -> FakeSettingsStore:
    return FakeSettingsStore()


@pytest.fixture
def launcher() -> FakeLauncher:
    return FakeLauncher()


@pytest.fixture
def opener() -> FakeOpener:
    return FakeOpener()


@pytest.fixture
def window(
    application: QApplication,
    skills_root: Path,
    store: FakeSettingsStore,
    launcher: FakeLauncher,
    opener: FakeOpener,
) -> Iterator[MainWindow]:
    store.settings = Settings(skills_root=str(skills_root))
    service = SkillLibraryService(
        repository=FileSystemSkillRepository(),
        settings_store=store,
        launcher=launcher,
        opener=opener,
        probe=FakeProbe(),
        paths=FakePaths(),
    )
    main = MainWindow(service, PythonMarkdownRenderer(), BundledAssets())
    main.show()
    yield main
    main.close()
