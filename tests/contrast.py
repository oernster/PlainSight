"""The one measure of whether text can be read on the fill behind it.

Shared by the application's palette tests and the setup program's, so the two
are held to the same arithmetic rather than to two copies of it that drift.
"""

from __future__ import annotations

AA_RATIO = 4.5
CHANNELS = (1, 3, 5)
HEX_PAIR = 2
FULL_CHANNEL = 255
LOW_THRESHOLD = 0.03928
LOW_DIVISOR = 12.92
OFFSET = 0.055
SCALE = 1.055
GAMMA = 2.4
RED_WEIGHT = 0.2126
GREEN_WEIGHT = 0.7152
BLUE_WEIGHT = 0.0722
NUDGE = 0.05


def _channel(value: float) -> float:
    if value <= LOW_THRESHOLD:
        return value / LOW_DIVISOR
    return ((value + OFFSET) / SCALE) ** GAMMA


def luminance(colour: str) -> float:
    """The relative luminance of a hex colour, as WCAG defines it."""
    red, green, blue = (
        _channel(int(colour[index : index + HEX_PAIR], 16) / FULL_CHANNEL)
        for index in CHANNELS
    )
    return RED_WEIGHT * red + GREEN_WEIGHT * green + BLUE_WEIGHT * blue


def contrast(front: str, back: str) -> float:
    """The contrast ratio between two hex colours."""
    first, second = luminance(front), luminance(back)
    return (max(first, second) + NUDGE) / (min(first, second) + NUDGE)
