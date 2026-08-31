"""Build the application into the bundle the setup program then wraps.

PyInstaller rather than Nuitka: this is a reader, not a runtime-heavy
application, so the shorter build and the simpler bundle are the better trade.

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

APP_DISPLAY_NAME = "Skills Viewer"
EXE_NAME = "SkillsViewer"
ENTRY_SCRIPT = PROJECT_ROOT / "main.py"
ICON_FILE = PROJECT_ROOT / "assets" / "skillsviewer.ico"
VERSION_FILE = PROJECT_ROOT / "VERSION"

ASSETS_DIR = PROJECT_ROOT / "assets"
LICENCE_FILES = (
    PROJECT_ROOT / "LICENSE",
    PROJECT_ROOT / "LICENSE-GPL-3.0.txt",
    PROJECT_ROOT / "LICENSE-LGPL-3.0.txt",
)

DIST_DIR = PROJECT_ROOT / "dist-pyinstaller"
WORK_DIR = PROJECT_ROOT / "build"
SPEC_FILE = PROJECT_ROOT / f"{EXE_NAME}.spec"

PAYLOAD_DIR = PROJECT_ROOT / "installer" / "payload"
BUNDLE_DIR = PAYLOAD_DIR / APP_DISPLAY_NAME

COLLECT_ALL = ("markdown",)

# PySide6 is deliberately NOT collected whole. Measured: --collect-all=PySide6
# produced a 726MB bundle by taking every Qt module, WebEngine and 3D included.
# PyInstaller's own PySide6 hook takes what is imported; these are the large
# modules nothing here reaches even indirectly.
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
    # with Pillow. The application itself imports neither; they were adding 34MB
    # to the bundle.
    "PIL",
    "numpy",
)


def run(command: list[str]) -> None:
    """Run one step, failing the build on a non-zero exit."""
    print("  " + " ".join(command))
    completed = subprocess.run(command, cwd=str(PROJECT_ROOT), check=False)
    if completed.returncode != 0:
        raise SystemExit(f"failed with exit {completed.returncode}")


def clean() -> None:
    """Remove the previous build; the spec is a regenerated artifact."""
    for path in (DIST_DIR, WORK_DIR, BUNDLE_DIR):
        shutil.rmtree(path, ignore_errors=True)
    SPEC_FILE.unlink(missing_ok=True)


MASTER_SUFFIX = "-master.png"


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
    """Every runtime file the application resolves beside its executable."""
    separator = os.pathsep
    arguments = [f"--add-data={asset}{separator}assets" for asset in shipped_assets()]
    arguments.append(f"--add-data={VERSION_FILE}{separator}.")
    for licence in LICENCE_FILES:
        if licence.is_file():
            arguments.append(f"--add-data={licence}{separator}.")
    return arguments


def build() -> None:
    """Bundle the application into dist-pyinstaller."""
    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        f"--name={EXE_NAME}",
        "--onedir",
        "--windowed",
        "--noconfirm",
        "--clean",
        f"--distpath={DIST_DIR}",
        f"--workpath={WORK_DIR}",
    ]
    if ICON_FILE.is_file():
        command.append(f"--icon={ICON_FILE}")
    command.extend(data_arguments())
    command.extend(f"--collect-all={package}" for package in COLLECT_ALL)
    command.extend(f"--exclude-module={module}" for module in EXCLUDED_MODULES)
    command.append(str(ENTRY_SCRIPT))
    run(command)


def stage() -> None:
    """Move the bundle where the setup program expects to find it.

    The removal is checked rather than ignored: a silent rmtree failure leaves
    the old directory in place, shutil.move then puts the new bundle INSIDE it,
    then the build reports success over a bundle whose executable is one level
    deeper than anything will look. Measured, not imagined.
    """
    built = DIST_DIR / EXE_NAME
    if not built.is_dir():
        raise SystemExit(f"no bundle at {built}")
    PAYLOAD_DIR.mkdir(parents=True, exist_ok=True)
    shutil.rmtree(BUNDLE_DIR, ignore_errors=True)
    if BUNDLE_DIR.exists():
        raise SystemExit(f"{BUNDLE_DIR} could not be removed; is it open?")
    shutil.move(str(built), str(BUNDLE_DIR))
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
