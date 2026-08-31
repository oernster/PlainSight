"""Where the setup program finds what the build put inside it.

Under a onefile build the payload sits beside the unpacked bootstrap rather
than beside the executable the user double-clicked, so every path is resolved
here rather than guessed at each call site.
"""

from __future__ import annotations

import os
import pathlib
import sys

PAYLOAD_DIRECTORY = "payload"
ARCHIVE_NAME = "SkillsViewer.zip"
MARK_NAME = "skillsviewer_icon_256.png"
LICENCE_NAME = "INSTALLER_LICENSE"
VERSION_NAME = "VERSION"
FALLBACK_VERSION = "0.0.0-dev"
NUITKA_LAUNCHER = "NUITKA_ONEFILE_BINARY"


def bundle_root() -> pathlib.Path:
    """The directory the build's own data was unpacked into."""
    bundled = getattr(sys, "_MEIPASS", None)
    if bundled is not None:
        return pathlib.Path(bundled)
    return pathlib.Path(__file__).resolve().parent.parent


def launcher_path() -> pathlib.Path:
    """The setup executable the user actually started.

    Under a Nuitka onefile build sys.executable points at the unpacked
    bootstrap rather than the real launcher, so the environment variable it
    sets is read first; PyInstaller has no equivalent problem.
    """
    named = os.environ.get(NUITKA_LAUNCHER)
    if named:
        return pathlib.Path(named)
    return pathlib.Path(sys.argv[0]).resolve()


def payload_directory() -> pathlib.Path:
    """Where the staged payload sits inside the build."""
    return bundle_root() / PAYLOAD_DIRECTORY


def archive_path() -> pathlib.Path:
    """The zipped application bundle."""
    return payload_directory() / ARCHIVE_NAME


def _find(name: str) -> pathlib.Path | None:
    for root in (bundle_root(), payload_directory()):
        candidate = root / name
        if candidate.is_file():
            return candidate
    return None


def mark_path() -> pathlib.Path | None:
    """The 126px mark in the header."""
    return _find(MARK_NAME) or _find(f"assets/{MARK_NAME}")


def licence_path() -> pathlib.Path | None:
    """The one licence the setup program itself carries."""
    return _find(LICENCE_NAME)


def read_version() -> str:
    """The version this setup program carries."""
    found = _find(VERSION_NAME)
    if found is None:
        return FALLBACK_VERSION
    return found.read_text(encoding="utf-8").strip() or FALLBACK_VERSION
