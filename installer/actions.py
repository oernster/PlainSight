"""What installing and removing actually do.

Everything is per user, so Windows never asks for an administrator: the files
go under %LOCALAPPDATA%\\Programs; the uninstall record goes under HKCU.
"""

from __future__ import annotations

import os
import pathlib
import shutil
import zipfile

from installer.plan import InstallPlan

APP_DISPLAY_NAME = "Skills Viewer"
EXE_NAME = "SkillsViewer.exe"
PAYLOAD_ARCHIVE = "SkillsViewer.zip"
PROGRAMS_DIRECTORY = "Programs"
SHORTCUT_NAME = f"{APP_DISPLAY_NAME}.lnk"
START_MENU_TAIL = ("Microsoft", "Windows", "Start Menu", "Programs")
UNINSTALLER_DIRECTORY = "_uninstall"
BYTES_PER_KILOBYTE = 1024


class ExtractionEscape(Exception):
    """An archive entry pointed outside the directory it is being written to."""


def local_app_data() -> pathlib.Path:
    """The per-user application directory for this account."""
    return pathlib.Path(os.environ.get("LOCALAPPDATA", str(pathlib.Path.home())))


def default_target() -> pathlib.Path:
    """Where the application goes unless the record says otherwise."""
    return local_app_data() / PROGRAMS_DIRECTORY / APP_DISPLAY_NAME


def desktop_directory() -> pathlib.Path:
    """This account's desktop."""
    return pathlib.Path.home() / "Desktop"


def start_menu_directory() -> pathlib.Path:
    """This account's Start menu programs folder."""
    return pathlib.Path(os.environ.get("APPDATA", str(pathlib.Path.home()))).joinpath(
        *START_MENU_TAIL
    )


def shortcut_paths() -> tuple[pathlib.Path, pathlib.Path]:
    """The desktop and Start menu shortcuts, wherever they would live."""
    return (
        desktop_directory() / SHORTCUT_NAME,
        start_menu_directory() / SHORTCUT_NAME,
    )


def safe_members(archive: zipfile.ZipFile, target: pathlib.Path) -> list[str]:
    """Every entry, checked against the target before any of them is written.

    Checked as a whole first rather than entry by entry, so a crafted archive
    cannot write half its contents before one entry is caught climbing out.
    """
    root = target.resolve()
    names: list[str] = []
    for name in archive.namelist():
        destination = (root / name).resolve()
        if not destination.is_relative_to(root):
            raise ExtractionEscape(name)
        names.append(name)
    return names


def extract_payload(archive_path: pathlib.Path, target: pathlib.Path) -> None:
    """Unpack the bundle into the install directory, fenced."""
    target.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive_path) as archive:
        archive.extractall(target, members=safe_members(archive, target))


def remove_tree(target: pathlib.Path) -> None:
    """Remove an install directory, tolerating one that is already gone."""
    shutil.rmtree(target, ignore_errors=True)


def install_size_kb(target: pathlib.Path) -> int:
    """The installed size, as the Apps list wants it."""
    if not target.is_dir():
        return 0
    total = sum(path.stat().st_size for path in target.rglob("*") if path.is_file())
    return total // BYTES_PER_KILOBYTE


def uninstaller_path(plan: InstallPlan) -> pathlib.Path:
    """Where the setup program copies itself so removal can re-run it."""
    return plan.target / UNINSTALLER_DIRECTORY / "SkillsViewerSetup.exe"


def executable_path(target: pathlib.Path) -> pathlib.Path:
    """The installed application."""
    return target / EXE_NAME
