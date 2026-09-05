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
import subprocess
import sys
import tempfile

import stamp_version
from build_utils import require, require_macos, run, section
from buildexe import (
    EXCLUDED_MODULES,
    INCLUDED_PACKAGES,
    parallel_jobs,
    shipped_assets,
)
from dmg_icon import png_to_icns, set_file_icon

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent

APP_DISPLAY_NAME = "PlainSight"
APP_NAME = "PlainSight"
BUNDLE_ID = "uk.codecrafter.PlainSight"
ENTRY_SCRIPT = PROJECT_ROOT / "main.py"
ICON_SOURCE = PROJECT_ROOT / "assets" / "plainsight_icon_1024.png"

DIST_DIR = PROJECT_ROOT / "dist"
WORK_DIR = PROJECT_ROOT / "build"
STAGING_DIR = PROJECT_ROOT / "dist-dmg-stage"
APP_BUNDLE = DIST_DIR / f"{APP_NAME}.app"
DMG_NAME = f"{APP_NAME}.dmg"
# The image lands in the repository root, beside the sources, rather than in
# dist: main() clears dist before every build, so an artefact kept there is
# gone the moment the next build starts.
DMG_PATH = PROJECT_ROOT / DMG_NAME

DEVELOPER_ID = os.environ.get(
    "DEVELOPER_ID_APPLICATION",
    "Developer ID Application: Oliver Ernster (W7K465GKFJ)",
)
APPLE_ID = os.environ.get("APPLE_ID", "")
APPLE_APP_PASSWORD = os.environ.get("APPLE_APP_PASSWORD", "")
APPLE_TEAM_ID = os.environ.get("APPLE_TEAM_ID", "W7K465GKFJ")
# A notarytool credential profile keeps the app-specific password in the
# login keychain, so it never reaches the environment or this file. Create
# it once with:
#   xcrun notarytool store-credentials "PlainSight" \
#       --apple-id <apple id> --team-id <team id>
NOTARY_PROFILE = os.environ.get("NOTARY_PROFILE", APP_NAME)

# PlainSight loads the Qt frameworks it ships, all signed with this same
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


def build_app(icns: pathlib.Path) -> None:
    """Compile the application into an app bundle.

    Nuitka does not sign as it builds, which PyInstaller did through
    --codesign-identity. That is no loss here: the stray object files have to
    go before the seal is applied anyway, so signing was always going to be its
    own step afterwards. It is sign_bundle that seals this.
    """
    section("Building the application bundle")
    jobs = parallel_jobs()
    print(f"  parallel jobs: {jobs}")
    command = [
        sys.executable,
        "-m",
        "nuitka",
        "--standalone",
        "--macos-create-app-bundle",
        "--assume-yes-for-downloads",
        "--enable-plugin=pyside6",
        "--deployment",
        "--lto=yes",
        f"--jobs={jobs}",
        f"--macos-app-name={APP_DISPLAY_NAME}",
        f"--macos-app-icon={icns}",
        f"--macos-app-version={stamp_version.read_version()}",
        f"--macos-signed-app-name={BUNDLE_ID}",
        f"--output-dir={DIST_DIR}",
        f"--include-data-file={PROJECT_ROOT / 'VERSION'}=VERSION",
    ]
    command.extend(
        f"--include-data-file={asset}=assets/{asset.name}" for asset in shipped_assets()
    )
    command.extend(f"--include-package={package}" for package in INCLUDED_PACKAGES)
    command.extend(f"--nofollow-import-to={module}" for module in EXCLUDED_MODULES)
    command.append(str(ENTRY_SCRIPT))
    run(command)
    place_bundle()


def place_bundle() -> None:
    """Move whatever Nuitka named the bundle to the name everything expects.

    Nuitka names it after the entry script, so main.py yields main.app. The
    glob is deliberate rather than a hardcoded main.app: the naming has moved
    between releases and a wrong guess here fails the signing step with a
    misleading message about a missing bundle.
    """
    if APP_BUNDLE.is_dir():
        return
    candidates = [path for path in DIST_DIR.glob("*.app") if path != APP_BUNDLE]
    if not candidates:
        raise SystemExit(f"no app bundle under {DIST_DIR}")
    shutil.move(str(candidates[0]), str(APP_BUNDLE))


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

    The volume icon is set through create-dmg rather than written afterwards:
    the finished image is read-only and compressed, so a later write of
    .VolumeIcon.icns has nowhere to land.
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
            "--volicon",
            str(icns),
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


def stored_credentials() -> str:
    """Empty when notarytool holds a usable profile, the reason when it does not.

    notarytool is asked rather than the keychain searched: it keeps its
    credentials in the data protection keychain, where security(1) cannot see
    them, so looking for a generic password finds nothing however good the
    profile is. One history call proves the profile exists AND authenticates.
    """
    asked = subprocess.run(
        ["xcrun", "notarytool", "history", "--keychain-profile", NOTARY_PROFILE],
        capture_output=True,
        text=True,
        check=False,
    )
    if asked.returncode == 0:
        return ""
    return asked.stderr.strip().splitlines()[0] if asked.stderr.strip() else "unusable"


def credentials() -> list[str]:
    """How to authenticate, preferring the keychain over the environment.

    A stored profile is preferred because it keeps the app-specific password
    out of the environment entirely. The environment pair stays as the fallback
    for a machine that has no profile, a build server for instance; the
    reason the profile was rejected is printed rather than swallowed, so a
    skipped notarization never looks like a deliberate one.
    """
    unusable = stored_credentials()
    if not unusable:
        return ["--keychain-profile", NOTARY_PROFILE]
    print(f"  {NOTARY_PROFILE} profile unusable: {unusable}")
    if APPLE_ID and APPLE_APP_PASSWORD:
        return [
            "--apple-id",
            APPLE_ID,
            "--password",
            APPLE_APP_PASSWORD,
            "--team-id",
            APPLE_TEAM_ID,
        ]
    return []


def notarize() -> None:
    """Submit and staple, only when there is something to authenticate with."""
    authentication = credentials()
    if not authentication:
        section(
            f"Notarizing skipped: no {NOTARY_PROFILE} credential profile and no "
            "APPLE_ID with APPLE_APP_PASSWORD"
        )
        return
    section("Notarizing")
    run(["xcrun", "notarytool", "submit", str(DMG_PATH), *authentication, "--wait"])
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

        build_app(icns)
        strip_object_files()
        sign_bundle(entitlements)
        create_dmg(icns)
        run(["codesign", "--force", "--sign", DEVELOPER_ID, str(DMG_PATH)])
        notarize()
        run(["codesign", "--verify", str(DMG_PATH)])
        # Last, because it is the only step that would be undone by another:
        # the icon rides in the resource fork, which stapling and signing both
        # rewrite the file around.
        set_file_icon(DMG_PATH, icns)
        section("Done")
        print(f"  {DMG_PATH.relative_to(PROJECT_ROOT)}")
    finally:
        entitlements.unlink(missing_ok=True)
        shutil.rmtree(STAGING_DIR, ignore_errors=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
