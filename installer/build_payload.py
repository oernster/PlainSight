"""Stage the built application as the opaque payload the setup program carries.

The bundle is ZIPPED rather than shipped loose: a onefile build strips loose
executables and libraries out of a bundled data directory, so a loose bundle
would not survive the wrap. As one archive it is opaque data the setup program
extracts at install time.

    python -m installer.build_payload
"""

from __future__ import annotations

import pathlib
import shutil
import sys

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent
APP_DISPLAY_NAME = "Skills Viewer"
ARCHIVE_STEM = "SkillsViewer"

PAYLOAD_DIR = PROJECT_ROOT / "installer" / "payload"
BUNDLE_DIR = PAYLOAD_DIR / APP_DISPLAY_NAME
ARCHIVE_PATH = PAYLOAD_DIR / f"{ARCHIVE_STEM}.zip"

CARRIED_FILES = (
    PROJECT_ROOT / "VERSION",
    PROJECT_ROOT / "INSTALLER_LICENSE",
)
# The setup program's own interface reads these, so they are staged beside the
# payload rather than left inside the zipped bundle it has not extracted yet.
CARRIED_ASSETS = (
    "skillsviewer_icon_256.png",
    "skillsviewer.ico",
    "light-mode.png",
    "dark-mode.png",
)


def stage() -> pathlib.Path:
    """Zip the bundle and copy what the setup program's own UI reads."""
    if not BUNDLE_DIR.is_dir():
        raise SystemExit(f"no bundle at {BUNDLE_DIR}; run buildexe.py first")
    ARCHIVE_PATH.unlink(missing_ok=True)
    shutil.make_archive(str(PAYLOAD_DIR / ARCHIVE_STEM), "zip", root_dir=BUNDLE_DIR)

    for carried in CARRIED_FILES:
        if carried.is_file():
            shutil.copy2(carried, PAYLOAD_DIR / carried.name)
    for name in CARRIED_ASSETS:
        asset = PROJECT_ROOT / "assets" / name
        if asset.is_file():
            shutil.copy2(asset, PAYLOAD_DIR / name)
    return ARCHIVE_PATH


def main() -> int:
    """Stage the payload, naming what was written."""
    archive = stage()
    print(f"  {archive.relative_to(PROJECT_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
