"""The two questions the application asks about the machine it runs on."""

from __future__ import annotations

from pathlib import Path

APPLICATION_DIRECTORY = "SkillsViewer"
SETTINGS_FILE_NAME = "settings.json"


class HomePlatformPaths:
    """Locations derived from the home directory of the current user."""

    def home_directory(self) -> str:
        """The current user's home directory."""
        return str(Path.home())


class FileSystemPathProbe:
    """Answers whether a path is there, without reading it."""

    def exists(self, path: str) -> bool:
        """Whether something exists at this path."""
        return Path(path).exists()


def settings_path() -> Path:
    """Where the settings file lives for the current user."""
    return Path.home() / f".{APPLICATION_DIRECTORY.lower()}" / SETTINGS_FILE_NAME
