"""Finds the bundled assets, wherever the application was packaged into.

Development, PyInstaller, Nuitka and a flatpak each put the assets somewhere
different, so every consumer asks here rather than building a path of its own.
"""

from __future__ import annotations

import sys
from pathlib import Path

ASSETS_DIRECTORY = "assets"
VERSION_FILE_NAME = "VERSION"
FALLBACK_VERSION = "0.0.0-dev"


def _candidate_roots() -> tuple[Path, ...]:
    """Every place the assets could sit, most likely first."""
    here = Path(__file__).resolve().parent.parent.parent
    roots = [here]
    bundled = getattr(sys, "_MEIPASS", None)
    if bundled is not None:
        roots.insert(0, Path(bundled))
    roots.append(Path(sys.argv[0]).resolve().parent)
    return tuple(roots)


def find_asset(name: str) -> Path | None:
    """The bundled asset of this name; None when it is not there."""
    for root in _candidate_roots():
        candidate = root / ASSETS_DIRECTORY / name
        if candidate.is_file():
            return candidate
    return None


def read_version() -> str:
    """The application version, read from the one file that holds it."""
    for root in _candidate_roots():
        candidate = root / VERSION_FILE_NAME
        if candidate.is_file():
            return candidate.read_text(encoding="utf-8").strip()
    return FALLBACK_VERSION


class BundledAssets:
    """Locates bundled artwork for the user interface."""

    def find(self, name: str) -> str | None:
        """The path of the bundled asset of this name; None when absent."""
        found = find_asset(name)
        return None if found is None else str(found)
