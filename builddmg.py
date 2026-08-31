"""Build, sign and notarize the macOS disk image.

Run from the repository root on macOS with the virtual environment active.
Notarizing is skipped unless both APPLE_ID and APPLE_APP_PASSWORD are set, so
the script is useful locally without credentials and complete with them.

    python builddmg.py
"""

from __future__ import annotations

import os
import pathlib
import shutil
import tempfile

import stamp_version
from build_utils import require, require_macos, run, section
from dmg_icon import png_to_icns, set_volume_icon

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent

APP_DISPLAY_NAME = "Skills Viewer"
APP_NAME = "SkillsViewer"
BUNDLE_ID = "uk.codecrafter.SkillsViewer"
ENTRY_SCRIPT = PROJECT_ROOT / "main.py"
ICON_SOURCE = PROJECT_ROOT / "assets" / "skillsviewer_icon_1024.png"

DIST_DIR = PROJECT_ROOT / "dist"
WORK_DIR = PROJECT_ROOT / "build"
STAGING_DIR = PROJECT_ROOT / "dist-dmg-stage"
APP_BUNDLE = DIST_DIR / f"{APP_NAME}.app"
DMG_NAME = "skillsviewer-macos-arm64.dmg"
DMG_PATH = DIST_DIR / DMG_NAME

COLLECT_ALL = ("PySide6", "shiboken6", "markdown")

DEVELOPER_ID = os.environ.get(
    "DEVELOPER_ID_APPLICATION",
    "Developer ID Application: Oliver Ernster (W7K465GKFJ)",
)
APPLE_ID = os.environ.get("APPLE_ID", "")
APPLE_APP_PASSWORD = os.environ.get("APPLE_APP_PASSWORD", "")
APPLE_TEAM_ID = os.environ.get("APPLE_TEAM_ID", "W7K465GKFJ")

# Skills Viewer loads the Qt frameworks it ships, all signed with this same
# identity, so library validation is the one entitlement it needs.
ENTITLEMENTS = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>com.apple.security.cs.disable-library-validation</key>
    <true/>
</dict>
</plist>
"""

DMG_WINDOW = ("--window-size", "620", "400")
CREATE_DMG_HEADLESS_EXIT = 2


def build_app(icns: pathlib.Path, entitlements: pathlib.Path) -> None:
    """Bundle the application, signed as it is built."""
    section("Building the application bundle")
    command = [
        require("pyinstaller"),
        "--noconfirm",
        "--clean",
        "--windowed",
        f"--name={APP_NAME}",
        f"--icon={icns}",
        f"--distpath={DIST_DIR}",
        f"--workpath={WORK_DIR}",
        f"--osx-bundle-identifier={BUNDLE_ID}",
        f"--codesign-identity={DEVELOPER_ID}",
        f"--osx-entitlements-file={entitlements}",
        f"--add-data={PROJECT_ROOT / 'assets'}:assets",
        f"--add-data={PROJECT_ROOT / 'VERSION'}:.",
    ]
    command.extend(f"--collect-all={package}" for package in COLLECT_ALL)
    command.append(str(ENTRY_SCRIPT))
    run(command)


def strip_object_files() -> int:
    """Remove the stray Mach-O objects PySide6 ships in its QML plugins.

    codesign --deep silently skips a .o file and Gatekeeper then rejects the
    bundle as containing unsigned code, so they go before signing rather than
    after a rejection.
    """
    section("Stripping stray object files")
    removed = 0
    for stray in APP_BUNDLE.rglob("*.o"):
        stray.unlink()
        removed += 1
    for directory in sorted(APP_BUNDLE.rglob("objects-*"), reverse=True):
        if directory.is_dir() and not any(directory.iterdir()):
            directory.rmdir()
    print(f"  removed {removed}")
    return removed


def sign_bundle(entitlements: pathlib.Path) -> None:
    """Seal the bundle, then read the seal back."""
    section("Signing")
    run(
        [
            "codesign",
            "--force",
            "--deep",
            "--options",
            "runtime",
            "--entitlements",
            str(entitlements),
            "--sign",
            DEVELOPER_ID,
            str(APP_BUNDLE),
        ]
    )
    run(["codesign", "--verify", "--deep", "--strict", str(APP_BUNDLE)])


def create_dmg(icns: pathlib.Path) -> None:
    """Stage with ditto, then build the image.

    ditto rather than a Python copy: dereferencing the framework symlinks
    invalidates the signatures embedded beneath them.
    """
    section("Creating the disk image")
    shutil.rmtree(STAGING_DIR, ignore_errors=True)
    STAGING_DIR.mkdir(parents=True)
    run(["ditto", str(APP_BUNDLE), str(STAGING_DIR / APP_BUNDLE.name)])

    DMG_PATH.unlink(missing_ok=True)
    completed = run(
        [
            require("create-dmg"),
            "--volname",
            APP_DISPLAY_NAME,
            *DMG_WINDOW,
            "--icon",
            APP_BUNDLE.name,
            "160",
            "180",
            "--app-drop-link",
            "440",
            "180",
            str(DMG_PATH),
            str(STAGING_DIR),
        ],
        check=False,
    )
    # create-dmg returns 2 when it could not set a custom window background,
    # which is the normal outcome headless and is not a failure.
    if completed.returncode not in (0, CREATE_DMG_HEADLESS_EXIT):
        raise SystemExit(f"create-dmg failed with exit {completed.returncode}")
    set_volume_icon(DMG_PATH, icns)


def notarize() -> None:
    """Submit and staple, only when both credentials are present."""
    if not (APPLE_ID and APPLE_APP_PASSWORD):
        section("Notarizing skipped: APPLE_ID and APPLE_APP_PASSWORD are not set")
        return
    section("Notarizing")
    run(
        [
            "xcrun",
            "notarytool",
            "submit",
            str(DMG_PATH),
            "--apple-id",
            APPLE_ID,
            "--password",
            APPLE_APP_PASSWORD,
            "--team-id",
            APPLE_TEAM_ID,
            "--wait",
        ]
    )
    run(["xcrun", "stapler", "staple", str(DMG_PATH)])


def main() -> int:
    """The whole macOS path, from a clean tree to a verified image."""
    require_macos()
    print(f"Building {APP_DISPLAY_NAME} {stamp_version.read_version()} for macOS")
    stamp_version.main()

    handle, entitlements_name = tempfile.mkstemp(suffix=".plist")
    entitlements = pathlib.Path(entitlements_name)
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            stream.write(ENTITLEMENTS)

        shutil.rmtree(DIST_DIR, ignore_errors=True)
        shutil.rmtree(WORK_DIR, ignore_errors=True)
        icns = png_to_icns(ICON_SOURCE, PROJECT_ROOT / f"{APP_NAME}.icns")

        build_app(icns, entitlements)
        strip_object_files()
        sign_bundle(entitlements)
        create_dmg(icns)
        run(["codesign", "--force", "--sign", DEVELOPER_ID, str(DMG_PATH)])
        notarize()
        run(["codesign", "--verify", str(DMG_PATH)])
        section("Done")
        print(f"  {DMG_PATH.relative_to(PROJECT_ROOT)}")
    finally:
        entitlements.unlink(missing_ok=True)
        shutil.rmtree(STAGING_DIR, ignore_errors=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
