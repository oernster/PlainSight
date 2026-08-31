"""Derive every platform icon asset from one master, plus the donate mark.

The master is a square RGBA PNG at the repository root. Nothing here upscales:
a master smaller than a wanted size is reported rather than stretched, because
an enlarged icon looks worse than a missing one and hides the real problem.

The donate mark does NOT go through the squaring path the icon takes. It is a
wide picture drawn at a button's height, so a square canvas would spend half
its height on nothing: it is cropped to its artwork and scaled by height alone.

Run it from the repository root:

    python generate_icons.py
"""

from __future__ import annotations

import pathlib
import sys

from PIL import Image

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent
MASTER_PNG = PROJECT_ROOT / "skillsviewer.png"
DONATE_MASTER = PROJECT_ROOT / "assets" / "donate-master.png"
ASSETS_DIR = PROJECT_ROOT / "assets"

PNG_SIZES = (16, 24, 32, 48, 64, 96, 128, 256, 512, 1024)
ICO_SIZES = (16, 24, 32, 48, 64, 128, 256)
CANONICAL_PNG_SIZE = 256
ICNS_SIZE = 1024

ICON_STEM = "skillsviewer_icon"
ICO_NAME = "skillsviewer.ico"
ICNS_NAME = "skillsviewer.icns"
CANONICAL_PNG_NAME = f"{ICON_STEM}.png"

# The button glyphs are drawn at this height, so each is written at four times
# it and stays crisp under display scaling.
BUTTON_ICON_PX = 28
BUTTON_SCALE = 4
DONATE_HEIGHT_PX = BUTTON_ICON_PX * BUTTON_SCALE
DONATE_NAME = "donate.png"

# The tray artwork, each derived from its own master beside it.
BUTTON_MARKS = (
    "file",
    "choose-editor",
    "launch-editor",
    "help-about",
    "ui-licence",
    "model-licence",
    "light-mode",
    "dark-mode",
)
MASTER_SUFFIX = "-master.png"

RESAMPLE = Image.Resampling.LANCZOS
NO_ALPHA = 0


def load_master(path: pathlib.Path) -> Image.Image:
    """The master as RGBA, centre cropped to a square."""
    image = Image.open(path).convert("RGBA")
    side = min(image.width, image.height)
    left = (image.width - side) // 2
    top = (image.height - side) // 2
    return image.crop((left, top, left + side, top + side))


def crop_to_artwork(image: Image.Image) -> Image.Image:
    """The tight box of the non-transparent pixels."""
    box = image.getchannel("A").getbbox()
    return image if box is None else image.crop(box)


def scale_to_height(image: Image.Image, height: int) -> Image.Image:
    """Scaled by height alone, keeping the aspect ratio."""
    width = max(1, round(image.width * height / image.height))
    return image.resize((width, height), RESAMPLE)


def write_icon_set(master: Image.Image) -> list[pathlib.Path]:
    """Every derived icon: the loose sizes, the canonical PNG, ico and icns."""
    written: list[pathlib.Path] = []
    for size in PNG_SIZES:
        path = ASSETS_DIR / f"{ICON_STEM}_{size}.png"
        master.resize((size, size), RESAMPLE).save(path)
        written.append(path)

    canonical = ASSETS_DIR / CANONICAL_PNG_NAME
    master.resize((CANONICAL_PNG_SIZE, CANONICAL_PNG_SIZE), RESAMPLE).save(canonical)
    written.append(canonical)

    ico = ASSETS_DIR / ICO_NAME
    largest = max(ICO_SIZES)
    master.resize((largest, largest), RESAMPLE).save(
        ico, format="ICO", sizes=[(size, size) for size in ICO_SIZES]
    )
    written.append(ico)

    icns = ASSETS_DIR / ICNS_NAME
    master.resize((ICNS_SIZE, ICNS_SIZE), RESAMPLE).save(icns, format="ICNS")
    written.append(icns)
    return written


def write_button_marks() -> list[pathlib.Path]:
    """Each tray glyph, from its own master, at the height it is drawn."""
    written: list[pathlib.Path] = []
    for name in BUTTON_MARKS:
        master_path = ASSETS_DIR / f"{name}{MASTER_SUFFIX}"
        if not master_path.is_file():
            continue
        mark = load_master(master_path).resize(
            (DONATE_HEIGHT_PX, DONATE_HEIGHT_PX), RESAMPLE
        )
        path = ASSETS_DIR / f"{name}.png"
        mark.save(path)
        written.append(path)
    return written


def write_donate_mark() -> pathlib.Path | None:
    """The donate artwork, cropped to itself and scaled by height."""
    if not DONATE_MASTER.is_file():
        return None
    mark = scale_to_height(
        crop_to_artwork(Image.open(DONATE_MASTER).convert("RGBA")), DONATE_HEIGHT_PX
    )
    path = ASSETS_DIR / DONATE_NAME
    mark.save(path)
    return path


def main() -> int:
    """Derive the whole set, reporting each file written."""
    if not MASTER_PNG.is_file():
        print(f"No master at {MASTER_PNG}", file=sys.stderr)
        return 1
    master = load_master(MASTER_PNG)
    if master.width < max(PNG_SIZES):
        print(
            f"Master is {master.width}px; {max(PNG_SIZES)}px is wanted. "
            "Nothing is upscaled, so that size is written at the master's own.",
            file=sys.stderr,
        )

    ASSETS_DIR.mkdir(exist_ok=True)
    written = write_icon_set(master)
    written.extend(write_button_marks())
    donate = write_donate_mark()
    if donate is not None:
        written.append(donate)
    for path in written:
        print(path.relative_to(PROJECT_ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
