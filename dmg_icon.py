"""Turning the master PNG into an icns, and putting it on the image itself."""

from __future__ import annotations

import pathlib
import struct
import subprocess

ICNS_SIZE = 1024

# Finder reads a file's own icon from an 'icns' resource at this well-known id
# in the resource fork, and only looks when the custom-icon flag is set in the
# FinderInfo attribute. Both halves are needed; either alone shows nothing.
CUSTOM_ICON_RESOURCE_ID = -16455
RESOURCE_TYPE = b"icns"
CUSTOM_ICON_FLAG = 0x0400
FINDER_INFO_ATTRIBUTE = "com.apple.FinderInfo"
FINDER_INFO_SIZE = 32
FINDER_FLAGS_OFFSET = 8
FINDER_FLAGS_SIZE = 2
RESOURCE_FORK = "..namedfork/rsrc"

# The resource fork layout, from Inside Macintosh: a 256 byte header, the
# resource data, then a map describing it. Rez writes this; it is spelled out
# here so the build needs no Xcode, only the command line tools everyone has.
HEADER_SIZE = 256
HEADER_FIELDS = 16
MAP_HEADER_SIZE = 28
TYPE_ENTRY_SIZE = 8
TYPE_COUNT_SIZE = 2
NO_RESOURCE_NAME = -1
FIRST_ITEM = 0
DATA_OFFSET_SIZE = 3


def png_to_icns(source: pathlib.Path, destination: pathlib.Path) -> pathlib.Path:
    """Write an icns from a large square PNG, with no iconutil needed."""
    from PIL import Image

    image = Image.open(source).convert("RGBA")
    image.resize((ICNS_SIZE, ICNS_SIZE), Image.Resampling.LANCZOS).save(
        destination, format="ICNS"
    )
    return destination


def set_file_icon(target: pathlib.Path, icns: pathlib.Path) -> None:
    """Give a file its own icon in Finder, rather than its type's icon.

    This is the icon on the .dmg sitting in a folder, which is a different
    thing from the volume icon create-dmg puts inside the image. The custom
    icon lives in the file's resource fork, so it does not touch the data fork
    and a signature over the image stays valid.
    """
    fork = target / RESOURCE_FORK
    fork.write_bytes(_resource_fork(icns.read_bytes()))
    _set_custom_icon_flag(target)


def _resource_fork(icns: bytes) -> bytes:
    """One icns resource, wrapped in the smallest valid resource fork."""
    data = struct.pack(">I", len(icns)) + icns
    reference_list_offset = TYPE_COUNT_SIZE + TYPE_ENTRY_SIZE
    type_list = (
        struct.pack(">H", FIRST_ITEM)
        + RESOURCE_TYPE
        + struct.pack(">HH", FIRST_ITEM, reference_list_offset)
    )
    reference_list = (
        struct.pack(">hh", CUSTOM_ICON_RESOURCE_ID, NO_RESOURCE_NAME)
        + bytes([FIRST_ITEM])
        + FIRST_ITEM.to_bytes(DATA_OFFSET_SIZE, "big")
        + struct.pack(">I", FIRST_ITEM)
    )
    body = type_list + reference_list
    name_list_offset = MAP_HEADER_SIZE + len(body)
    resource_map = (
        bytes(HEADER_FIELDS)
        + struct.pack(">IHH", FIRST_ITEM, FIRST_ITEM, FIRST_ITEM)
        + struct.pack(">HH", MAP_HEADER_SIZE, name_list_offset)
        + body
    )
    header = struct.pack(
        ">IIII", HEADER_SIZE, HEADER_SIZE + len(data), len(data), len(resource_map)
    )
    return header + bytes(HEADER_SIZE - len(header)) + data + resource_map


def _set_custom_icon_flag(target: pathlib.Path) -> None:
    """Turn the flag on in place, keeping the type and creator already there.

    xattr rather than SetFile, which lives inside Xcode and is not on every
    machine. Overwriting the whole attribute would strip the disk image's own
    type and creator, so the existing value is read back and edited.
    """
    listed = subprocess.run(
        ["xattr", "-px", FINDER_INFO_ATTRIBUTE, str(target)],
        capture_output=True,
        text=True,
        check=False,
    )
    if listed.returncode == 0 and listed.stdout.split():
        info = bytearray(int(byte, 16) for byte in listed.stdout.split())
    else:
        info = bytearray(FINDER_INFO_SIZE)
    end = FINDER_FLAGS_OFFSET + FINDER_FLAGS_SIZE
    flags = int.from_bytes(info[FINDER_FLAGS_OFFSET:end], "big") | CUSTOM_ICON_FLAG
    info[FINDER_FLAGS_OFFSET:end] = flags.to_bytes(FINDER_FLAGS_SIZE, "big")
    subprocess.run(
        ["xattr", "-wx", FINDER_INFO_ATTRIBUTE, info.hex(), str(target)], check=True
    )
