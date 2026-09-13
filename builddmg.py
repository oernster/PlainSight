"""macOS DMG builder for PlainSight.

Requires macOS with Xcode command-line tools and Homebrew.
Run from the repository root with the venv active:
    python builddmg.py

Notarization is mandatory. A Developer ID signature alone is not enough: since
macOS 10.15 Gatekeeper rejects signed-but-unnotarized apps with "Apple could not
verify ... is free of malware". Credentials come from this app's keychain
profile (NOTARY_PROFILE), stored once with `xcrun notarytool store-credentials`,
so nothing needs to be exported to run a release build.

The shape follows Stellody's builddmg.py, which ships notarized: nested binaries
signed innermost first with a secure timestamp, the bundle notarized and stapled
before it goes into the image, then the image itself signed, notarized, stapled
and assessed the way Gatekeeper will assess it.

Env vars:
    APPLE_KEYCHAIN_PROFILE    : override the per-app keychain profile
    APPLE_ID                  : Apple ID, for CI that has no keychain
    APPLE_APP_PASSWORD        : app-specific password, paired with APPLE_ID
    DEVELOPER_ID_APPLICATION  : override the default signing identity
    APPLE_TEAM_ID             : Team ID for notarization. Read from the signing
                                identity when unset, since Apple prints it there
    ALLOW_UNNOTARIZED         : set to 1 to build without notarizing. The result
                                is for local testing only and must never be
                                published as a release artifact.
"""

from __future__ import annotations

import os
import plistlib
import re
import shutil
import subprocess
import sys
import tempfile
from importlib import metadata
from pathlib import Path

import stamp_version
from build_utils import require, require_macos, run, section
from buildexe import (
    EXCLUDED_MODULES,
    INCLUDED_PACKAGES,
    LICENCE_FILES,
    parallel_jobs,
    shipped_assets,
)
from dmg_icon import set_file_icon

ROOT = Path(__file__).resolve().parent

# -- Constants ----------------------------------------------------------------

APP_NAME = "PlainSight"
APP_VERSION = stamp_version.read_version()
BUNDLE_ID = "uk.codecrafter.PlainSight"
# The download page links to this exact name, so it is not lowercased the way
# Stellody's is.
FINAL_DMG = f"{APP_NAME}.dmg"
VOLUME_NAME = APP_NAME

ENTRY_SCRIPT = ROOT / "main.py"
DIST_DIR = ROOT / "dist"
STAGING_DIR = "dist-dmg-stage"

# Written by generate_icons.py from the master artwork, which is the one place
# any icon in this project comes from. Read rather than derived here.
ICNS_FILE = ROOT / "assets" / "plainsight.icns"

# Everything Nuitka lays down goes here, so the payload check and the search
# for binaries to sign both read one place rather than each spelling it out.
BUNDLE_PAYLOAD_DIR = "Contents/MacOS"
# The Info.plist key naming the bundle's own executable.
MAIN_EXECUTABLE_KEY = "CFBundleExecutable"
# Where data belongs in a bundle, which is not beside the executable.
BUNDLE_RESOURCES_NAME = "Resources"
BUNDLE_RESOURCES_DIR = f"Contents/{BUNDLE_RESOURCES_NAME}"
PARENT_DIR = "../"

# The runtime looks for these beside its executable (resources.py for the
# assets and VERSION, dialogs.py for the licences), so they land there first
# and are relocated into Resources with a symlink left in their place.
ASSETS_DESTINATION = "assets"
VERSION_FILE = ROOT / "VERSION"

DEVELOPER_ID = os.environ.get(
    "DEVELOPER_ID_APPLICATION",
    "Developer ID Application: Oliver Ernster (W7K465GKFJ)",
)
APPLE_ID = os.environ.get("APPLE_ID", "")
APPLE_APP_PASSWORD = os.environ.get("APPLE_APP_PASSWORD", "")

# Apple prints the Team ID in parentheses at the end of every Developer ID
# identity, so it is read from the identity rather than written down twice
# where the two could drift apart. APPLE_TEAM_ID overrides it.
TEAM_ID_RE = re.compile(r"\(([A-Z0-9]+)\)\s*$")
_team_id_match = TEAM_ID_RE.search(DEVELOPER_ID)
APPLE_TEAM_ID = os.environ.get("APPLE_TEAM_ID", "") or (
    _team_id_match.group(1) if _team_id_match else ""
)

# The notarization credential for this app, created once with
#   xcrun notarytool store-credentials PlainSight \
#     --apple-id <id> --team-id <team> --password <app-specific>
# One profile per app means a leaked credential can be revoked for a single
# app. APPLE_KEYCHAIN_PROFILE overrides it.
NOTARY_PROFILE = os.environ.get("APPLE_KEYCHAIN_PROFILE", "") or APP_NAME

# The notary service accepts only an app-specific password from appleid.apple.com
# and rejects the Apple account password with HTTP 401. The shape is distinctive,
# so it is checked before the build rather than discovered after it.
APP_SPECIFIC_PASSWORD_RE = re.compile(r"^[a-z]{4}-[a-z]{4}-[a-z]{4}-[a-z]{4}$")

# Escape hatch for local test builds. Distribution builds must never set this:
# an unnotarized DMG is rejected by Gatekeeper on every machine but the one that
# signed it; the failure is invisible at build time.
ALLOW_UNNOTARIZED = os.environ.get("ALLOW_UNNOTARIZED", "") == "1"

# Notarization is the default. The only way to skip it is to ask for that
# explicitly: the previous script skipped it silently whenever the keychain
# profile was missing, which produced an image that signed cleanly and was then
# rejected by Gatekeeper as "Unnotarized Developer ID".
NOTARIZING = not ALLOW_UNNOTARIZED

REQUIREMENT_NAME_RE = re.compile(r"^[A-Za-z0-9._-]+")

APPLE_TOOLS = ("codesign", "xcrun", "ditto", "hdiutil", "spctl", "xattr")

# The options every signature in this build carries. The hardened runtime is
# what notarization checks for; the timestamp is what keeps a signature valid
# after the certificate that made it expires.
SIGN_OPTIONS = ("--force", "--options", "runtime", "--timestamp")

# The first four bytes of a Mach-O binary: 64-bit, 32-bit and the two byte
# orders of a universal file. Read from the file itself, since a name says
# nothing reliable about whether something is code.
MACH_O_MAGICS = (
    b"\xcf\xfa\xed\xfe",
    b"\xce\xfa\xed\xfe",
    b"\xca\xfe\xba\xbe",
    b"\xbe\xba\xfe\xca",
)
MACH_O_MAGIC_LENGTH = 4

BYTES_PER_MIB = 1024 * 1024
CREATE_DMG_OK = (0, 2)  # 2 means it could not set a window background, headless

# Minimal hardened-runtime entitlements. PlainSight reads local documents, has
# no JIT and reaches the network only for its update check, which needs no
# entitlement outside the sandbox. disable-library-validation lets the hardened
# runtime load the bundled Qt frameworks signed with our identity.
ENTITLEMENTS = """\
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>com.apple.security.cs.disable-library-validation</key>
    <true/>
</dict>
</plist>
"""


def data_files() -> tuple[Path, ...]:
    """The loose files shipped at the bundle root: VERSION plus the licences."""
    return (VERSION_FILE, *LICENCE_FILES)


# -- Steps --------------------------------------------------------------------


def check_platform() -> None:
    section("Platform check")
    require_macos()
    result = subprocess.run(
        ["sw_vers", "-productVersion"], capture_output=True, text=True, check=False
    )
    print(f"  macOS {result.stdout.strip()}")
    require("create-dmg", "create-dmg")
    # These arrive with the Xcode command-line tools rather than from Homebrew,
    # so asking brew for them (which require() would do) offers a remedy that
    # cannot work.
    missing = [tool for tool in APPLE_TOOLS if not shutil.which(tool)]
    if missing:
        sys.exit(
            f"ERROR: {', '.join(missing)} not found.\n"
            "  Install the Xcode command-line tools:\n"
            "    xcode-select --install"
        )
    print("  All tools present.")


def check_notarization_credentials() -> None:
    """Fail before the build starts if the release cannot be notarized.

    Checked up front rather than at the notarization step so a missing
    credential costs seconds instead of a full compile. The keychain profile is
    proved by asking notarytool for its history: notarytool keeps the profile
    in the data protection keychain, where security(1) cannot see it, so one
    history call is the only check that shows it exists AND authenticates.
    """
    section("Notarization credentials")
    if ALLOW_UNNOTARIZED:
        print("  WARNING: ALLOW_UNNOTARIZED=1 set.")
        print("  WARNING: this build is for local testing and must not be released.")
        return
    if APPLE_ID and APPLE_APP_PASSWORD:
        if not APPLE_TEAM_ID:
            sys.exit(
                "ERROR: no Team ID.\n"
                f"  It could not be read from the signing identity {DEVELOPER_ID}\n"
                "  and APPLE_TEAM_ID is unset. Set APPLE_TEAM_ID; alternatively\n"
                "  leave APPLE_ID and APPLE_APP_PASSWORD unset and use the keychain\n"
                f"  profile {NOTARY_PROFILE}, which carries the Team ID already."
            )
        if not APP_SPECIFIC_PASSWORD_RE.match(APPLE_APP_PASSWORD):
            sys.exit(
                "ERROR: APPLE_APP_PASSWORD is not an app-specific password.\n"
                "  Expected four lowercase groups of four, like abcd-efgh-ijkl-mnop.\n"
                "  An Apple account password is rejected by the notary service with\n"
                "  'HTTP status code: 401. Invalid credentials'.\n"
                "  Generate one at https://appleid.apple.com (Sign-In and Security,\n"
                "  App-Specific Passwords); or leave both variables unset and store\n"
                f"  the credential in the keychain as profile {NOTARY_PROFILE}."
            )
        print(f"  Notarizing as {APPLE_ID} (team {APPLE_TEAM_ID}).")
        return
    asked = subprocess.run(
        ["xcrun", "notarytool", "history", "--keychain-profile", NOTARY_PROFILE],
        capture_output=True,
        text=True,
        check=False,
    )
    if asked.returncode != 0:
        sys.exit(
            f"ERROR: keychain profile {NOTARY_PROFILE} is unusable:\n"
            f"  {asked.stderr.strip() or asked.stdout.strip()}\n"
            "  Store it once (notarytool prompts for the app-specific password):\n"
            f"    xcrun notarytool store-credentials {NOTARY_PROFILE} "
            f"--apple-id you@example.com --team-id {APPLE_TEAM_ID}\n"
            "  Or set ALLOW_UNNOTARIZED=1 for a local test build."
        )
    print(f"  Notarizing with keychain profile {NOTARY_PROFILE}.")


def check_runtime_dependencies() -> None:
    """Fail if anything in requirements.txt is absent from the build interpreter.

    A packager only warns when it cannot find a package, so a stale venv yields
    a bundle that builds, signs and notarizes cleanly then dies at launch with
    ModuleNotFoundError. Checking the interpreter that is about to be compiled
    turns a silent runtime failure into a build failure.
    """
    section("Runtime dependencies")
    requirements = ROOT / "requirements.txt"
    if not requirements.exists():
        sys.exit(f"ERROR: {requirements.name} not found beside builddmg.py.")

    missing: list[str] = []
    checked = 0
    for raw in requirements.read_text(encoding="utf-8").splitlines():
        line = raw.split("#")[0].strip()
        if not line or line.startswith("-"):
            continue
        # The distribution name only. Stellody parses with packaging to honour
        # environment markers; this file carries none, so the stdlib match keeps
        # the build free of a dependency the About credits would have to name.
        name = REQUIREMENT_NAME_RE.match(line)
        if name is None:
            sys.exit(f"ERROR: cannot parse '{line}' in {requirements.name}")
        checked += 1
        try:
            metadata.version(name.group(0))
        except metadata.PackageNotFoundError:
            missing.append(name.group(0))

    if missing:
        sys.exit(
            "ERROR: the build interpreter is missing "
            f"{len(missing)} of {checked} requirements:\n"
            + "".join(f"    {name}\n" for name in missing)
            + "  The build would omit them and the app would crash at launch\n"
            "  with ModuleNotFoundError. Install them first:\n"
            f"    pip install -r {requirements.name}"
        )
    print(f"  All {checked} requirements present.")


def check_bundled_assets() -> None:
    """A named file that is not on disk FAILS the build rather than being skipped.

    Skipping produces a bundle that launches perfectly with controls wearing no
    pictures, discoverable only by running the packaged application and looking,
    while the build itself reports success.
    """
    section("Bundled assets")
    missing = [str(path) for path in data_files() if not path.is_file()]
    if not ICNS_FILE.is_file():
        missing.append(f"{ICNS_FILE} (run: python generate_icons.py)")
    if not shipped_assets():
        missing.append("assets/ holds no derived artwork")
    if missing:
        sys.exit(
            "ERROR: these are named for the bundle but not on disk:\n  "
            + "\n  ".join(missing)
        )
    print(f"  {len(data_files())} file(s), {len(shipped_assets())} asset(s), icon.")


def notarytool_credentials() -> list[str]:
    """Authentication arguments for notarytool.

    An explicit APPLE_ID and APPLE_APP_PASSWORD pair wins, for CI that has no
    keychain. Otherwise the per-app profile is used, which keeps the secret out
    of the process arguments where any other process could read it via ps.
    """
    if APPLE_ID and APPLE_APP_PASSWORD:
        return [
            "--apple-id",
            APPLE_ID,
            "--password",
            APPLE_APP_PASSWORD,
            "--team-id",
            APPLE_TEAM_ID,
        ]
    return ["--keychain-profile", NOTARY_PROFILE]


def redact(cmd: list[str]) -> str:
    """Render a command with the value after --password masked.

    build_utils.run echoes every command it runs, which would otherwise copy the
    app-specific password into build logs and CI output.
    """
    parts: list[str] = []
    mask_next = False
    for arg in (str(item) for item in cmd):
        parts.append("********" if mask_next else arg)
        mask_next = arg == "--password"
    return " ".join(parts)


def notarytool_submit(target: Path) -> None:
    """Submit target to Apple and wait for the verdict.

    A failed submission stops the build rather than producing an artifact that
    looks distributable. subprocess is called directly instead of through run()
    so that neither the echoed command nor the failure path exposes the
    password. Stapling is a separate step because the submitted file and the
    file that carries the ticket differ for a .app (a zip is submitted; the
    bundle is stapled).
    """
    cmd = [
        "xcrun",
        "notarytool",
        "submit",
        str(target),
        *notarytool_credentials(),
        "--wait",
    ]
    print(f"  $ {redact(cmd)}")
    if subprocess.run(cmd, check=False).returncode == 0:
        return
    sys.exit(
        "ERROR: notarization failed (notarytool output above).\n"
        "  'HTTP status code: 401' means the credential is wrong: use an\n"
        "  app-specific password, not your Apple account password.\n"
        "  For an 'Invalid' verdict, the per-binary reasons are in:\n"
        "    xcrun notarytool log <submission-id> "
        f"--keychain-profile {NOTARY_PROFILE}"
    )


def clean() -> None:
    section("Clean previous build")
    for name in ["build", "dist", FINAL_DMG, STAGING_DIR]:
        path = ROOT / name
        if not path.exists():
            continue
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()
        print(f"  Removed: {name}")


def build_app_bundle() -> Path:
    """Compile the application into a .app bundle with Nuitka.

    Nuitka names the bundle after the entry script rather than after the
    application, so what it produces is found by looking rather than by being
    told, then moved to the name everything after this expects.
    """
    section("Nuitka: build .app bundle")

    cmd = [
        sys.executable,
        "-m",
        "nuitka",
        "--standalone",
        "--macos-create-app-bundle",
        "--assume-yes-for-downloads",
        "--enable-plugin=pyside6",
        "--deployment",
        "--lto=yes",
        f"--jobs={parallel_jobs()}",
        f"--macos-app-name={APP_NAME}",
        f"--macos-app-version={APP_VERSION}",
        f"--macos-app-icon={ICNS_FILE}",
        f"--macos-signed-app-name={BUNDLE_ID}",
        f"--output-dir={DIST_DIR}",
    ]
    cmd.extend(f"--include-data-file={item}={item.name}" for item in data_files())
    cmd.extend(
        f"--include-data-file={asset}={ASSETS_DESTINATION}/{asset.name}"
        for asset in shipped_assets()
    )
    cmd.extend(f"--include-package={package}" for package in INCLUDED_PACKAGES)
    cmd.extend(f"--nofollow-import-to={module}" for module in EXCLUDED_MODULES)
    cmd.append(str(ENTRY_SCRIPT))

    run(cmd)

    produced = sorted(DIST_DIR.glob("*.app"))
    if not produced:
        sys.exit(f"ERROR: Nuitka produced no .app bundle in {DIST_DIR}")
    app_path = DIST_DIR / f"{APP_NAME}.app"
    if produced[0] != app_path:
        if app_path.exists():
            shutil.rmtree(app_path)
        produced[0].rename(app_path)
    print(f"  Built: {app_path}")
    return app_path


def relocated_names() -> list[str]:
    """What the bundle carries beside its executable that is data, not code."""
    return [item.name for item in data_files()] + [ASSETS_DESTINATION]


def check_bundle_payload(app_path: Path) -> None:
    """Fail if the compiled bundle is short of anything it was told to carry.

    check_bundled_assets proves the sources exist before the build; this proves
    they arrived. A missing asset is invisible until the packaged application is
    run and looked at, which is far too late to learn it.
    """
    section("Bundle payload")
    payload = app_path / BUNDLE_PAYLOAD_DIR
    expected = [item.name for item in data_files()]
    expected += [f"{ASSETS_DESTINATION}/{asset.name}" for asset in shipped_assets()]
    missing = [name for name in expected if not (payload / name).exists()]
    if missing:
        sys.exit(
            "ERROR: the bundle is missing:\n  "
            + "\n  ".join(missing)
            + f"\n  Looked in {payload}."
        )
    print(f"  {len(expected)} expected item(s) present.")


def relocate_bundle_resources(app_path: Path) -> None:
    """Move the shipped data into Contents/Resources, leaving symlinks behind.

    codesign treats everything sitting beside the main executable as code, so a
    plain file there fails the bundle signature with "code object is not signed
    at all. In subcomponent: ... LICENSE". Apple's layout keeps data in
    Contents/Resources, which is where these belong.

    The symlink keeps the runtime lookups working: resources.py and dialogs.py
    look beside the executable, which is still exactly where they find them.
    """
    section("Relocate bundle resources")
    payload = app_path / BUNDLE_PAYLOAD_DIR
    resources = app_path / BUNDLE_RESOURCES_DIR
    names = relocated_names()
    for name in names:
        placed = payload / name
        if placed.is_symlink():
            continue
        relocated = resources / name
        relocated.parent.mkdir(parents=True, exist_ok=True)
        placed.rename(relocated)
        # One ".." to climb out of Contents/MacOS, plus one for each directory
        # the name itself descends into.
        climb = PARENT_DIR * (name.count("/") + 1)
        placed.symlink_to(Path(climb) / BUNDLE_RESOURCES_NAME / name)
    print(f"  {len(names)} item(s) moved to {BUNDLE_RESOURCES_DIR}, symlinked back.")


def strip_build_artifacts(app_path: Path) -> None:
    section("Strip build artifacts")
    # PySide6 ships .cpp.o object files inside its QML plugin directories.
    # They are Mach-O relocatable objects: not loadable code, so signing them
    # means nothing, while leaving them unsigned has Gatekeeper reject the
    # whole bundle. They are removed before anything is signed for that reason.
    removed = 0
    for found in app_path.rglob("*.o"):
        if found.is_file():
            found.unlink()
            removed += 1
    for directory in sorted(app_path.rglob("objects-*"), reverse=True):
        if directory.is_dir() and not any(directory.iterdir()):
            directory.rmdir()
    print(f"  Removed {removed} intermediate object file(s)")


def _mach_o_files(app_path: Path) -> list[Path]:
    """Every Mach-O file in the bundle, deepest first.

    Recognised by the file's own magic number rather than by its name: the
    bundle carries binaries called .so, .dylib and nothing at all, while a data
    file whose name merely ends that way is not code and must not be signed.
    Symlinks are skipped, since signing one signs its target twice.
    """
    found: list[Path] = []
    for path in app_path.rglob("*"):
        if path.is_symlink() or not path.is_file():
            continue
        with path.open("rb") as handle:
            if handle.read(MACH_O_MAGIC_LENGTH) in MACH_O_MAGICS:
                found.append(path)
    return sorted(found, key=lambda item: len(item.parts), reverse=True)


def _main_executable(app_path: Path) -> Path:
    """The bundle's own executable, read from the Info.plist that names it.

    It is signed as part of the bundle and never on its own: codesign resolves
    a lone main executable back to the bundle around it, then fails on the
    first data file sitting beside it.
    """
    info = plistlib.loads((app_path / "Contents" / "Info.plist").read_bytes())
    return app_path / BUNDLE_PAYLOAD_DIR / info[MAIN_EXECUTABLE_KEY]


def sign_bundle(app_path: Path, entitlements_path: Path) -> None:
    """Sign the nested binaries innermost first, then the bundle itself.

    Not codesign --deep, which has been deprecated for signing since macOS 13
    and applies all signing options (entitlements included) to all nested
    content. The entitlements describe the application, so they are given to
    the bundle alone.

    --timestamp is explicit because notarization requires a secure timestamp on
    every signature, which is not a thing to leave to a default.
    """
    section("Code signing")
    # codesign refuses a file carrying Finder information or a resource fork.
    run(["xattr", "-cr", str(app_path)])

    main_executable = _main_executable(app_path)
    binaries = [item for item in _mach_o_files(app_path) if item != main_executable]
    print(f"  Signing {len(binaries)} nested binaries, deepest first.")
    for binary in binaries:
        # subprocess directly rather than run(): echoing one line per binary
        # would bury the rest of the build in output nobody reads.
        subprocess.run(
            ["codesign", *SIGN_OPTIONS, "--sign", DEVELOPER_ID, str(binary)],
            check=True,
        )

    run(
        [
            "codesign",
            *SIGN_OPTIONS,
            "--entitlements",
            str(entitlements_path),
            "--sign",
            DEVELOPER_ID,
            str(app_path),
        ]
    )
    run(["codesign", "--verify", "--deep", "--strict", str(app_path)])
    print("  Signature verified.")


def notarize_bundle(app_path: Path) -> None:
    """Notarize and staple the .app before it is placed in the DMG.

    Stapling only the DMG leaves the copied-out .app with no local ticket, so
    Gatekeeper falls back to an online check and the app fails to launch for a
    user who is offline or behind a restrictive network. notarytool only accepts
    archives, so the bundle is zipped with ditto first (ditto preserves the
    symlinks and metadata the embedded signature depends on); the ticket is then
    stapled to the bundle itself, since a zip cannot carry one.
    """
    if not NOTARIZING:
        return
    section("Notarize .app bundle")
    with tempfile.TemporaryDirectory() as tmp:
        archive = Path(tmp) / f"{APP_NAME}.zip"
        run(["ditto", "-c", "-k", "--keepParent", str(app_path), str(archive)])
        notarytool_submit(archive)
    run(["xcrun", "stapler", "staple", str(app_path)])
    print("  Bundle notarized and stapled.")


def create_dmg(app_path: Path) -> None:
    """Stage with ditto, then build the image.

    The volume icon is set through create-dmg rather than written afterwards:
    the finished image is read-only and compressed, so a later write of
    .VolumeIcon.icns has nowhere to land.
    """
    section("Create DMG")

    staging = ROOT / STAGING_DIR
    shutil.rmtree(staging, ignore_errors=True)
    staging.mkdir()
    dest = staging / app_path.name
    # ditto preserves the symlinks macOS frameworks rely on (e.g.
    # Python.framework/Python -> Versions/Current/Python). Dereferencing them
    # into regular files invalidates every embedded code signature and causes
    # dlopen failures at runtime.
    run(["ditto", str(app_path), str(dest)])

    final = ROOT / FINAL_DMG
    final.unlink(missing_ok=True)

    cmd = [
        "create-dmg",
        "--volname",
        VOLUME_NAME,
        "--volicon",
        str(ICNS_FILE),
        "--window-size",
        "620",
        "400",
        "--icon",
        app_path.name,
        "160",
        "180",
        "--app-drop-link",
        "440",
        "180",
        str(final),
        str(staging),
    ]

    try:
        result = run(cmd, check=False)
    finally:
        shutil.rmtree(staging, ignore_errors=True)
    if result.returncode not in CREATE_DMG_OK:
        sys.exit(f"ERROR: create-dmg failed (exit {result.returncode})")
    print(f"  DMG created: {FINAL_DMG}")


def apply_file_icon() -> None:
    """Give the .dmg sitting in a folder its own icon in Finder.

    Runs before the image is signed and notarized, as Stellody's does: the icon
    lives in the resource fork and FinderInfo, which stapling preserves.
    """
    section("Apply file icon")
    set_file_icon(ROOT / FINAL_DMG, ICNS_FILE)
    print(f"  Icon applied to {FINAL_DMG}")


def sign_dmg() -> None:
    section("Sign DMG")
    # No hardened runtime on a disk image, which holds no code of its own; the
    # timestamp matters here for the same reason it does on the bundle.
    run(
        [
            "codesign",
            "--force",
            "--timestamp",
            "--sign",
            DEVELOPER_ID,
            str(ROOT / FINAL_DMG),
        ]
    )
    print("  DMG signed.")


def notarize_dmg() -> None:
    if not NOTARIZING:
        return
    section("Notarize DMG")
    notarytool_submit(ROOT / FINAL_DMG)
    run(["xcrun", "stapler", "staple", str(ROOT / FINAL_DMG)])
    print("  Notarization complete and stapled.")


def verify_dmg() -> None:
    section("Verify DMG")
    final = ROOT / FINAL_DMG
    run(["codesign", "--verify", str(final)])
    size_mib = final.stat().st_size / BYTES_PER_MIB
    if not NOTARIZING:
        print(f"  {FINAL_DMG}  ({size_mib:.1f} MiB): UNNOTARIZED, local testing only")
        return
    # stapler validate proves a ticket is attached; spctl replays the check
    # Gatekeeper performs on the end user's machine. Together they catch the
    # silent case where signing succeeded but notarization never happened.
    run(["xcrun", "stapler", "validate", str(final)])
    # The assessment Gatekeeper makes when a user opens a disk image. "install"
    # is the assessment for an installer package, which this is not.
    run(
        [
            "spctl",
            "--assess",
            "--type",
            "open",
            "--context",
            "context:primary-signature",
            "-vv",
            str(final),
        ]
    )
    print(f"  {FINAL_DMG}  ({size_mib:.1f} MiB): notarized, ready for distribution")


# -- Main ---------------------------------------------------------------------


def main() -> int:
    print(f"\nPLAINSIGHT DMG BUILDER  v{APP_VERSION}")
    print(f"Signing identity: {DEVELOPER_ID}")

    check_platform()
    check_runtime_dependencies()
    check_bundled_assets()
    check_notarization_credentials()
    stamp_version.main()
    clean()

    with tempfile.NamedTemporaryFile(
        suffix=".entitlements", mode="w", delete=False
    ) as handle:
        handle.write(ENTITLEMENTS)
        entitlements_path = Path(handle.name)

    try:
        app_path = build_app_bundle()
        check_bundle_payload(app_path)
        relocate_bundle_resources(app_path)
        strip_build_artifacts(app_path)
        sign_bundle(app_path, entitlements_path)
        notarize_bundle(app_path)
        create_dmg(app_path)
        # The icon step rewrites the file's metadata, so it runs before the
        # image is signed and notarized.
        apply_file_icon()
        sign_dmg()
        notarize_dmg()
        verify_dmg()
    finally:
        entitlements_path.unlink(missing_ok=True)

    print(f"\nDone.  Distribute: {FINAL_DMG}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
