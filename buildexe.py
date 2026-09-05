"""Build the application into the bundle the setup program then wraps.

Nuitka rather than PyInstaller: the application is compiled to C rather than
frozen beside an interpreter, which is the house toolchain for a packaged
runtime and what the setup program's own wrap expects.

Two settings are deliberate and stated here rather than left to a reader of the
flag list. Compilation runs across every core the machine reports, falling back
to one when it reports none, since `os.cpu_count()` is documented to return
None. The release build is a deployment build: Nuitka's compatibility aids are
off and the onefile payload downstream keeps its compression, which is on by
default and is never disabled here.

    python buildexe.py
"""

from __future__ import annotations

import os
import pathlib
import shutil
import subprocess
import sys

import stamp_version

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent

APP_DISPLAY_NAME = "PlainSight"
APP_DESCRIPTION = "A reader for your documents"
APP_AUTHOR = "Oliver Ernster"
EXE_NAME = "PlainSight"
ENTRY_SCRIPT = PROJECT_ROOT / "main.py"
ICON_FILE = PROJECT_ROOT / "assets" / "plainsight.ico"
VERSION_FILE = PROJECT_ROOT / "VERSION"

ASSETS_DIR = PROJECT_ROOT / "assets"
LICENCE_FILES = (
    PROJECT_ROOT / "LICENSE",
    PROJECT_ROOT / "LICENSE-GPL-3.0.txt",
    PROJECT_ROOT / "LICENSE-LGPL-3.0.txt",
)

PAYLOAD_DIR = PROJECT_ROOT / "installer" / "payload"
BUNDLE_DIR = PAYLOAD_DIR / APP_DISPLAY_NAME
# Nuitka names its output after the entry script, so main.py yields main.dist.
NUITKA_OUTPUT_DIR = PAYLOAD_DIR / f"{ENTRY_SCRIPT.stem}.dist"
NUITKA_BUILD_DIR = PAYLOAD_DIR / f"{ENTRY_SCRIPT.stem}.build"

# One job per logical core. os.cpu_count() is documented to return None where
# the machine will not say, which is the whole reason for the fallback.
DEFAULT_JOBS = 1

# A Windows PE version is four numeric parts, so a three-part semantic version
# is padded rather than passed through.
PE_VERSION_PARTS = 4
PE_VERSION_PAD = "0"

CONSOLE_MODE_RELEASE = "disable"
CONSOLE_MODE_DEBUG = "attach"
DEBUG_ENVIRONMENT_FLAG = "PLAINSIGHT_BUILD_DEBUG"

# markdown loads its extensions by name at runtime, so following the imports it
# is written with does not reach them; the package goes in whole.
#
# docx and pypdf go in whole for the same reason: both reach parts of
# themselves by name rather than by import, docx through its content type map
# and pypdf through the filters a given file asks for. Read in the installed
# source rather than assumed: docx.api.Document loads the bundled default
# template only when it is called with no path; this application always
# calls it with one, so no package data has to travel with it.
INCLUDED_PACKAGES = ("markdown", "docx", "pypdf")

# Measured under PyInstaller and carried over deliberately: collecting Qt whole
# produced a 726MB bundle by taking WebEngine, 3D and Quick with it. Nuitka
# follows imports rather than collecting, so this is a fence rather than the
# load-bearing saving it was. It stays because nothing here reaches any of them
# even indirectly.
EXCLUDED_MODULES = (
    "PySide6.QtWebEngineCore",
    "PySide6.QtWebEngineWidgets",
    "PySide6.QtWebEngineQuick",
    "PySide6.Qt3DCore",
    "PySide6.Qt3DRender",
    "PySide6.Qt3DExtras",
    "PySide6.QtCharts",
    "PySide6.QtDataVisualization",
    "PySide6.QtMultimedia",
    "PySide6.QtMultimediaWidgets",
    "PySide6.QtQuick3D",
    "PySide6.QtBluetooth",
    "PySide6.QtNfc",
    "PySide6.QtPositioning",
    "PySide6.QtSerialPort",
    "PySide6.QtSql",
    "PySide6.QtTest",
    "PySide6.QtQml",
    "PySide6.QtQuick",
    "PySide6.QtQuickWidgets",
    "tkinter",
    # Pillow and numpy are build-time only: generate_icons.py reads the master
    # with Pillow. The application itself imports neither.
    "PIL",
    "numpy",
)

MASTER_SUFFIX = "-master.png"
ASSETS_DESTINATION = "assets"


def run(command: list[str]) -> None:
    """Run one step, failing the build on a non-zero exit."""
    print("  " + " ".join(command))
    completed = subprocess.run(command, cwd=str(PROJECT_ROOT), check=False)
    if completed.returncode != 0:
        raise SystemExit(f"failed with exit {completed.returncode}")


def parallel_jobs() -> str:
    """One compile job per logical core; one where the machine will not say."""
    return str(os.cpu_count() or DEFAULT_JOBS)


def pe_version() -> str:
    """The version as the four numeric parts a Windows PE field wants."""
    parts = stamp_version.read_version().split(".")
    numeric = [part for part in parts if part.isdigit()]
    while len(numeric) < PE_VERSION_PARTS:
        numeric.append(PE_VERSION_PAD)
    return ".".join(numeric[:PE_VERSION_PARTS])


def console_mode() -> str:
    """Release hides the console; a debug build keeps it attached."""
    return (
        CONSOLE_MODE_DEBUG
        if os.environ.get(DEBUG_ENVIRONMENT_FLAG)
        else CONSOLE_MODE_RELEASE
    )


def clean() -> None:
    """Remove the previous build, output and staging alike."""
    for path in (NUITKA_OUTPUT_DIR, NUITKA_BUILD_DIR, BUNDLE_DIR):
        shutil.rmtree(path, ignore_errors=True)


def shipped_assets() -> list[pathlib.Path]:
    """The derived artwork only.

    The masters are build inputs of several megabytes each; the application
    reads the derived files beside them and never opens a master.
    """
    return [
        path
        for path in sorted(ASSETS_DIR.iterdir())
        if path.is_file() and not path.name.endswith(MASTER_SUFFIX)
    ]


def data_arguments() -> list[str]:
    """Every runtime file the application resolves beside its executable.

    The destination is spelled out per file rather than given as a directory:
    the masters sit in the same folder and must not ship, so the folder cannot
    go in whole.
    """
    arguments = [
        f"--include-data-file={asset}={ASSETS_DESTINATION}/{asset.name}"
        for asset in shipped_assets()
    ]
    arguments.append(f"--include-data-file={VERSION_FILE}={VERSION_FILE.name}")
    for licence in LICENCE_FILES:
        if licence.is_file():
            arguments.append(f"--include-data-file={licence}={licence.name}")
    return arguments


def build() -> None:
    """Compile the application into a standalone bundle."""
    jobs = parallel_jobs()
    print(f"  parallel jobs: {jobs}")
    command = [
        sys.executable,
        "-m",
        "nuitka",
        "--standalone",
        "--assume-yes-for-downloads",
        "--enable-plugin=pyside6",
        "--deployment",
        "--lto=yes",
        f"--jobs={jobs}",
        f"--windows-console-mode={console_mode()}",
        f"--output-dir={PAYLOAD_DIR}",
        f"--output-filename={EXE_NAME}.exe",
        f"--company-name={APP_AUTHOR}",
        f"--product-name={APP_DISPLAY_NAME}",
        f"--file-version={pe_version()}",
        f"--product-version={pe_version()}",
        f"--file-description={APP_DESCRIPTION}",
        f"--copyright=Copyright {APP_AUTHOR}",
    ]
    if ICON_FILE.is_file():
        command.append(f"--windows-icon-from-ico={ICON_FILE}")
    command.extend(data_arguments())
    command.extend(f"--include-package={package}" for package in INCLUDED_PACKAGES)
    command.extend(f"--nofollow-import-to={module}" for module in EXCLUDED_MODULES)
    command.append(str(ENTRY_SCRIPT))
    run(command)


def stage() -> None:
    """Move the bundle where the setup program expects to find it.

    The removal is checked rather than ignored: a silent rmtree failure leaves
    the old directory in place, shutil.move then puts the new bundle INSIDE it,
    then the build reports success over a bundle whose executable is one level
    deeper than anything will look. Measured, not imagined.
    """
    if not NUITKA_OUTPUT_DIR.is_dir():
        raise SystemExit(f"no bundle at {NUITKA_OUTPUT_DIR}")
    PAYLOAD_DIR.mkdir(parents=True, exist_ok=True)
    shutil.rmtree(BUNDLE_DIR, ignore_errors=True)
    if BUNDLE_DIR.exists():
        raise SystemExit(f"{BUNDLE_DIR} could not be removed; is it open?")
    shutil.move(str(NUITKA_OUTPUT_DIR), str(BUNDLE_DIR))
    shutil.rmtree(NUITKA_BUILD_DIR, ignore_errors=True)
    executable = BUNDLE_DIR / f"{EXE_NAME}.exe"
    if not executable.is_file():
        raise SystemExit(f"no executable at {executable} after staging")
    print(f"  staged {BUNDLE_DIR.relative_to(PROJECT_ROOT)}")


def main() -> int:
    """Stamp, clean, build, stage."""
    print(f"Building {APP_DISPLAY_NAME} {stamp_version.read_version()}")
    stamp_version.main()
    clean()
    build()
    stage()
    print(f"  {(BUNDLE_DIR / f'{EXE_NAME}.exe').relative_to(PROJECT_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
