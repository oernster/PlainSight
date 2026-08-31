"""Turning the master into an icns, then putting it on the disk image."""

from __future__ import annotations

import pathlib
import subprocess

from build_utils import run

ICNS_SIZE = 1024
CUSTOM_ICON_ATTRIBUTE = "com.apple.FinderInfo"
# The kHasCustomIcon bit, written as the FinderInfo blob Finder reads.
CUSTOM_ICON_BLOB = "0000000000000000040000000000000000000000000000000000000000000000"


def png_to_icns(source: pathlib.Path, destination: pathlib.Path) -> pathlib.Path:
    """Write an icns from a large square PNG, with no iconutil needed."""
    from PIL import Image

    image = Image.open(source).convert("RGBA")
    image.resize((ICNS_SIZE, ICNS_SIZE), Image.Resampling.LANCZOS).save(
        destination, format="ICNS"
    )
    return destination


def set_volume_icon(dmg: pathlib.Path, icns: pathlib.Path) -> bool:
    """Give the mounted image a custom icon; False when the flag would not set.

    The FinderInfo bit is written with xattr rather than SetFile, which lives
    inside Xcode and is not on every machine.
    """
    attached = run(["hdiutil", "attach", str(dmg), "-nobrowse"], check=False)
    if attached.returncode != 0:
        return False
    try:
        mounted = _mount_point(dmg)
        if mounted is None:
            return False
        run(["cp", str(icns), str(mounted / ".VolumeIcon.icns")], check=False)
        run(
            ["xattr", "-wx", CUSTOM_ICON_ATTRIBUTE, CUSTOM_ICON_BLOB, str(mounted)],
            check=False,
        )
        return True
    finally:
        run(["hdiutil", "detach", str(dmg)], check=False)


def _mount_point(dmg: pathlib.Path) -> pathlib.Path | None:
    """Where the image was mounted, read back rather than assumed."""
    listed = subprocess.run(
        ["hdiutil", "info"], capture_output=True, text=True, check=False
    )
    for line in listed.stdout.splitlines():
        if "/Volumes/" in line:
            return pathlib.Path(line.split("\t")[-1].strip())
    return None
