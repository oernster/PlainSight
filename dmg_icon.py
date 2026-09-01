"""Turning the master PNG into the icns every macOS artefact points at."""

from __future__ import annotations

import pathlib

ICNS_SIZE = 1024


def png_to_icns(source: pathlib.Path, destination: pathlib.Path) -> pathlib.Path:
    """Write an icns from a large square PNG, with no iconutil needed."""
    from PIL import Image

    image = Image.open(source).convert("RGBA")
    image.resize((ICNS_SIZE, ICNS_SIZE), Image.Resampling.LANCZOS).save(
        destination, format="ICNS"
    )
    return destination
