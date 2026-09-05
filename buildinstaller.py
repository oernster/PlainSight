"""Wrap the built bundle into one per-user setup executable.

The bundle goes in as a ZIP rather than as loose files: a onefile build strips
loose executables and libraries out of a bundled data directory, so a loose
bundle would not survive the wrap.

The onefile payload is compressed. That is Nuitka's default and the only thing
this script does about it is never pass --onefile-no-compression; the
non-commercial build exposes no compression level to choose between. As in
buildexe.py the compile runs one job per logical core and the result is a
deployment build.

    python buildinstaller.py
"""

from __future__ import annotations

import pathlib
import shutil
import subprocess
import sys
import time

import stamp_version
from buildexe import (
    APP_AUTHOR,
    APP_DESCRIPTION,
    EXCLUDED_MODULES,
    ICON_FILE,
    parallel_jobs,
    pe_version,
)
from installer.build_payload import ARCHIVE_PATH, PAYLOAD_DIR, stage

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent

APP_DISPLAY_NAME = "PlainSight"
SETUP_NAME = "PlainSightSetup"
INSTALLER_ENTRY = PROJECT_ROOT / "installer" / "app.py"
VERSION_FILE = PROJECT_ROOT / "VERSION"

DIST_DIR = PROJECT_ROOT / "dist-installer"
TEMP_DIST_DIR = PROJECT_ROOT / "dist-installer.build"

PAYLOAD_DESTINATION = "payload"
CONSOLE_MODE = "disable"

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
    """Remove the previous wrap."""
    shutil.rmtree(TEMP_DIST_DIR, ignore_errors=True)


def build() -> None:
    """Wrap the staged payload into one compressed executable."""
    jobs = parallel_jobs()
    print(f"  parallel jobs: {jobs}")
    command = [
        sys.executable,
        "-m",
        "nuitka",
        "--onefile",
        "--assume-yes-for-downloads",
        "--enable-plugin=pyside6",
        "--deployment",
        "--lto=yes",
        f"--jobs={jobs}",
        f"--windows-console-mode={CONSOLE_MODE}",
        f"--output-dir={TEMP_DIST_DIR}",
        f"--output-filename={SETUP_NAME}.exe",
        f"--company-name={APP_AUTHOR}",
        f"--product-name={APP_DISPLAY_NAME} Setup",
        f"--file-version={pe_version()}",
        f"--product-version={pe_version()}",
        f"--file-description={APP_DESCRIPTION} Installer",
        f"--copyright=Copyright {APP_AUTHOR}",
        f"--include-data-dir={PAYLOAD_DIR}={PAYLOAD_DESTINATION}",
        f"--include-data-file={VERSION_FILE}={VERSION_FILE.name}",
    ]
    if ICON_FILE.is_file():
        command.append(f"--windows-icon-from-ico={ICON_FILE}")
    # The same exclusions the application takes; the setup program reaches even
    # less of Qt than it does.
    command.extend(f"--nofollow-import-to={module}" for module in EXCLUDED_MODULES)
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
