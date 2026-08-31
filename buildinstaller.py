"""Wrap the built bundle into one per-user setup executable.

The bundle goes in as a ZIP rather than as loose files: a onefile build strips
loose executables and libraries out of a bundled data directory, so a loose
bundle would not survive the wrap.

    python buildinstaller.py
"""

from __future__ import annotations

import pathlib
import shutil
import subprocess
import sys
import time

import stamp_version
from buildexe import EXCLUDED_MODULES
from installer.build_payload import ARCHIVE_PATH, PAYLOAD_DIR, stage

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent

APP_DISPLAY_NAME = "Skills Viewer"
SETUP_NAME = "SkillsViewerSetup"
INSTALLER_ENTRY = PROJECT_ROOT / "installer" / "app.py"
ICON_FILE = PROJECT_ROOT / "assets" / "skillsviewer.ico"

DIST_DIR = PROJECT_ROOT / "dist-installer"
TEMP_DIST_DIR = PROJECT_ROOT / "dist-installer.build"
WORK_DIR = PROJECT_ROOT / "build" / "installer"
SPEC_FILE = PROJECT_ROOT / f"{SETUP_NAME}.spec"

# Antivirus and Explorer both hold a new executable open for a moment, so the
# move into place retries rather than failing the whole build.
UNLINK_TRIES = 20
UNLINK_DELAY_S = 0.15


def run(command: list[str]) -> None:
    """Run one step, failing the build on a non-zero exit."""
    print("  " + " ".join(command))
    completed = subprocess.run(command, cwd=str(PROJECT_ROOT), check=False)
    if completed.returncode != 0:
        raise SystemExit(f"failed with exit {completed.returncode}")


def clean() -> None:
    """Remove the previous wrap; the spec is a regenerated artifact."""
    shutil.rmtree(TEMP_DIST_DIR, ignore_errors=True)
    shutil.rmtree(WORK_DIR, ignore_errors=True)
    SPEC_FILE.unlink(missing_ok=True)


def build() -> None:
    """Wrap the staged payload into one executable."""
    separator = ";" if sys.platform == "win32" else ":"
    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onefile",
        "--windowed",
        f"--name={SETUP_NAME}",
        f"--paths={PROJECT_ROOT}",
        f"--distpath={TEMP_DIST_DIR}",
        f"--workpath={WORK_DIR}",
        f"--add-data={PAYLOAD_DIR}{separator}payload",
    ]
    if ICON_FILE.is_file():
        command.append(f"--icon={ICON_FILE}")
    # The same exclusions the application takes; the setup program reaches even
    # less of Qt than it does.
    command.extend(f"--exclude-module={module}" for module in EXCLUDED_MODULES)
    command.append(str(INSTALLER_ENTRY))
    run(command)


def place() -> pathlib.Path:
    """Move the wrapped executable into dist-installer, retrying the unlink."""
    built = TEMP_DIST_DIR / f"{SETUP_NAME}.exe"
    if not built.is_file():
        built = TEMP_DIST_DIR / SETUP_NAME
    if not built.is_file():
        raise SystemExit(f"no setup program at {built}")

    DIST_DIR.mkdir(exist_ok=True)
    destination = DIST_DIR / built.name
    for attempt in range(UNLINK_TRIES):
        try:
            destination.unlink(missing_ok=True)
            break
        except OSError:
            if attempt == UNLINK_TRIES - 1:
                raise
            time.sleep(UNLINK_DELAY_S)
    shutil.move(str(built), str(destination))
    shutil.rmtree(TEMP_DIST_DIR, ignore_errors=True)
    return destination


def main() -> int:
    """Stamp, stage the payload, wrap it, place the result."""
    print(f"Wrapping {APP_DISPLAY_NAME} {stamp_version.read_version()}")
    stamp_version.main()
    stage()
    if not ARCHIVE_PATH.is_file():
        raise SystemExit(f"no payload archive at {ARCHIVE_PATH}")
    clean()
    build()
    placed = place()
    print(f"  {placed.relative_to(PROJECT_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
