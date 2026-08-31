"""Hand-written stand-ins for the application's ports.

Written rather than generated, so each one records exactly what a test needs to
assert about it and nothing more.
"""

from __future__ import annotations

from skillsviewer.domain.catalogue import SkillCatalogue
from skillsviewer.domain.settings import EditorChoice, Settings
from skillsviewer.domain.skill import Skill


def a_skill(name: str = "prose") -> Skill:
    """A readable skill, for tests that need one rather than describe one."""
    return Skill(
        name=name,
        description="",
        directory=f"/skills/{name}",
        document_path=f"/skills/{name}/SKILL.md",
        body="body",
    )


class FakeRepository:
    """Reports a fixed catalogue and records every root it was asked for."""

    def __init__(
        self,
        catalogue: SkillCatalogue | None = None,
        plugin_catalogue: SkillCatalogue | None = None,
    ) -> None:
        self.catalogue = catalogue if catalogue is not None else SkillCatalogue()
        self.plugin_catalogue = (
            plugin_catalogue if plugin_catalogue is not None else SkillCatalogue()
        )
        self.roots_read: list[str] = []
        self.plugin_roots_read: list[str] = []

    def list_skills(self, root: str) -> SkillCatalogue:
        self.roots_read.append(root)
        return self.catalogue

    def list_plugin_skills(self, root: str) -> SkillCatalogue:
        self.plugin_roots_read.append(root)
        return self.plugin_catalogue


class FakeSettingsStore:
    """Holds settings in memory and counts the saves."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings if settings is not None else Settings()
        self.saved: list[Settings] = []

    def load(self) -> Settings:
        return self.settings

    def save(self, settings: Settings) -> None:
        self.settings = settings
        self.saved.append(settings)


class FakeLauncher:
    """Records what it was asked to open; answers as it was told to."""

    def __init__(self, accepts: bool = True) -> None:
        self.accepts = accepts
        self.launched: list[tuple[EditorChoice, str]] = []

    def launch(self, editor: EditorChoice, target: str) -> bool:
        self.launched.append((editor, target))
        return self.accepts


class FakeOpener:
    """Records the addresses it was handed."""

    def __init__(self, accepts: bool = True) -> None:
        self.accepts = accepts
        self.opened: list[str] = []

    def open(self, address: str) -> bool:
        self.opened.append(address)
        return self.accepts


class FakeProbe:
    """Says a fixed set of paths are there and nothing else is."""

    def __init__(self, present: tuple[str, ...] = ()) -> None:
        self.present = set(present)

    def exists(self, path: str) -> bool:
        return path in self.present


class FakePaths:
    """A home directory chosen by the test rather than by the machine."""

    def __init__(self, home: str = "/home/oliver") -> None:
        self.home = home

    def home_directory(self) -> str:
        return self.home
