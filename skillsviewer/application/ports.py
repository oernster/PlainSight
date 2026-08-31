"""The seams the application talks through. Infrastructure implements them."""

from __future__ import annotations

from typing import Protocol

from ..domain.catalogue import SkillCatalogue
from ..domain.settings import EditorChoice, Settings


class SkillRepository(Protocol):
    """Reads a root and reports the skills it holds."""

    def list_skills(self, root: str) -> SkillCatalogue:
        """Every skill beneath ``root``, in display order."""
        ...

    def list_plugin_skills(self, root: str) -> SkillCatalogue:
        """Every skill held anywhere beneath a plugins tree."""
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


class AssetLocator(Protocol):
    """Finds the artwork the build bundled, wherever it was packaged into."""

    def find(self, name: str) -> str | None:
        """The path of the bundled asset of this name; None when absent."""
        ...


class MarkdownRenderer(Protocol):
    """Turns a skill's body into something a reading surface can show."""

    def render(self, body: str) -> str:
        """The body as HTML."""
        ...
