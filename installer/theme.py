"""The setup program's palette and its whole stylesheet.

A stylesheet in its own right rather than a layer over the application's: that
one carries the same ring model but a different geometry; the two would
fight. The colours are the application's own, so the two read as one product.

Sizes are in pixels, not points: a point-sized layout and a pixel-sized one
drift apart on the same display.
"""

from __future__ import annotations

from dataclasses import dataclass

MARK_PX = 126
HEADER_GAP_PX = 18
BODY_MARGIN_PX = 34
FOOTER_GAP_PX = 10
BAND_GAP_PX = 16
MARK_BUTTON_PX = 40
MARK_ICON_PX = 26
WINDOW_WIDTH_PX = 720
WINDOW_HEIGHT_PX = 560
TITLE_PX = 32
TAGLINE_PX = 14
HEADING_PX = 22
BODY_PX = 14
RADIUS_PX = 9
BORDER_PX = 2
GLOW_ALPHA = 38


@dataclass(frozen=True, slots=True)
class Palette:
    """Every colour the setup program draws with."""

    window: str
    surface: str
    alt: str
    text: str
    muted: str
    accent: str
    accent_soft: str
    selection: str
    ring: str
    danger: str
    danger_soft: str
    hairline: str


DARK = Palette(
    window="#12151c",
    surface="#1a1f29",
    alt="#232936",
    text="#e6e9f0",
    muted="#96a0b5",
    accent="#7c6cf0",
    accent_soft="#2a2547",
    selection="#2f2a52",
    ring="#22c55e",
    danger="#ef4444",
    danger_soft="#3a1f22",
    hairline="#2b3240",
)

LIGHT = Palette(
    window="#f5f6fa",
    surface="#ffffff",
    alt="#eceef5",
    text="#161a22",
    muted="#5b6478",
    accent="#5a49d6",
    accent_soft="#e6e2fb",
    selection="#ded8fa",
    ring="#059669",
    danger="#b91c1c",
    danger_soft="#fbe3e3",
    hairline="#d7dbe6",
)


def glow(palette: Palette) -> str:
    """A wash of the accent behind everything, derived rather than picked."""
    red, green, blue = (
        int(palette.accent[index : index + 2], 16) for index in (1, 3, 5)
    )
    return f"rgba({red}, {green}, {blue}, {GLOW_ALPHA})"


def stylesheet(palette: Palette) -> str:
    """The whole sheet, built from one palette.

    Every named button carries its own ring rule: an object-name rule setting
    a border beats the generic one by id specificity and would otherwise leave
    that button with no ring at all.
    """
    return f"""
* {{
    outline: none;
}}
QWidget {{
    background: transparent;
    color: {palette.text};
    font-size: {BODY_PX}px;
}}
QWidget#Shell {{
    background: qradialgradient(cx:0.5, cy:0, radius:1.1,
        stop:0 {glow(palette)}, stop:1 {palette.window});
}}
QLabel#Title {{
    font-size: {TITLE_PX}px;
    font-weight: 700;
}}
QLabel#Tagline {{
    font-size: {TAGLINE_PX}px;
    color: {palette.muted};
}}
QLabel#Heading {{
    font-size: {HEADING_PX}px;
    font-weight: 600;
}}
QLabel#Lead, QLabel#Muted {{
    color: {palette.muted};
}}
QLabel#Flow {{
    color: {palette.accent};
    font-weight: 600;
}}
QFrame#Rule {{
    background: {palette.hairline};
    max-height: 1px;
    border: none;
}}
QPushButton {{
    background: {palette.alt};
    color: {palette.text};
    border: {BORDER_PX}px solid transparent;
    border-radius: {RADIUS_PX}px;
    padding: 11px 22px;
    font-weight: 600;
}}
QPushButton:enabled:hover, QPushButton:enabled:focus {{
    border-color: {palette.ring};
}}
QPushButton:disabled {{
    background: {palette.surface};
    color: {palette.muted};
    border: {BORDER_PX}px solid {palette.danger};
}}
QPushButton#Primary {{
    background: {palette.selection};
    color: {palette.accent};
    border: {BORDER_PX}px solid transparent;
}}
QPushButton#Primary:enabled:hover, QPushButton#Primary:enabled:focus {{
    border-color: {palette.ring};
}}
QPushButton#Danger {{
    background: {palette.danger_soft};
    color: {palette.danger};
    border: {BORDER_PX}px solid transparent;
}}
QPushButton#Danger:enabled:hover, QPushButton#Danger:enabled:focus {{
    border-color: {palette.ring};
}}
QPushButton#Link {{
    background: transparent;
    color: {palette.muted};
    padding: 6px 10px;
    font-weight: 500;
    border: {BORDER_PX}px solid transparent;
}}
QPushButton#Link:enabled:hover, QPushButton#Link:enabled:focus {{
    border-color: {palette.ring};
}}
QPushButton#Mark {{
    background: transparent;
    padding: 4px;
    border: {BORDER_PX}px solid transparent;
    border-radius: {RADIUS_PX}px;
}}
QPushButton#Mark:enabled:hover, QPushButton#Mark:enabled:focus {{
    border-color: {palette.ring};
}}
QCheckBox {{
    spacing: 10px;
}}
QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    border-radius: 4px;
    border: {BORDER_PX}px solid {palette.hairline};
    background: {palette.surface};
}}
QCheckBox::indicator:checked {{
    background: {palette.accent};
    border-color: {palette.accent};
}}
QProgressBar {{
    background: {palette.surface};
    border: none;
    border-radius: 5px;
    height: 10px;
    text-align: center;
    color: transparent;
}}
QProgressBar::chunk {{
    background: {palette.accent};
    border-radius: 5px;
}}
QTextBrowser {{
    background: {palette.surface};
    border: {BORDER_PX}px solid transparent;
    border-radius: {RADIUS_PX}px;
    padding: 10px;
}}
QTextBrowser:enabled:focus {{
    border-color: {palette.ring};
}}
"""
