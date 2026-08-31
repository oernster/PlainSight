"""One home for every colour value, plus the stylesheet built from them.

The ring model has exactly three states: nothing at rest, green while a control
is hovered or focused and enabled, permanent red while it is disabled. The
accent is never a ring; it carries meaning only.
"""

from __future__ import annotations

from dataclasses import dataclass

BORDER_WIDTH_PX = 2
THIN_BORDER_WIDTH_PX = 1
RADIUS_PX = 6


@dataclass(frozen=True, slots=True)
class Palette:
    """Every colour the application draws with."""

    window: str
    panel: str
    control: str
    text: str
    muted: str
    accent: str
    ring: str
    danger: str
    selection_text: str
    code_background: str


DARK = Palette(
    window="#12151c",
    panel="#1a1f29",
    control="#232936",
    text="#e6e9f0",
    muted="#96a0b5",
    accent="#7c6cf0",
    ring="#22c55e",
    danger="#ef4444",
    selection_text="#ffffff",
    code_background="#0e1117",
)


def stylesheet(palette: Palette) -> str:
    """The application stylesheet, built from one palette.

    A container class never appears in a ring rule. The skill list is an item
    view, so it takes no ring in any state: its current row is the indicator.
    The reading pane is a scrolling region, so it rings on focus only.
    """
    return f"""
* {{
    outline: none;
}}
QWidget {{
    background: {palette.window};
    color: {palette.text};
    font-size: 14px;
}}
QMainWindow, QDialog {{
    background: {palette.window};
}}
QStatusBar {{
    background: {palette.panel};
    color: {palette.muted};
}}
QPushButton {{
    background: {palette.control};
    color: {palette.text};
    border: {BORDER_WIDTH_PX}px solid transparent;
    border-radius: {RADIUS_PX}px;
    padding: 6px 12px;
}}
QPushButton:enabled:hover, QPushButton:enabled:focus {{
    border-color: {palette.ring};
}}
QPushButton:disabled {{
    background: {palette.panel};
    color: {palette.muted};
    border: {BORDER_WIDTH_PX}px solid {palette.danger};
}}
QPushButton#IconButton {{
    background: {palette.control};
    border: {BORDER_WIDTH_PX}px solid transparent;
    border-radius: {RADIUS_PX}px;
    padding: 4px;
}}
QPushButton#IconButton:enabled:hover, QPushButton#IconButton:enabled:focus {{
    border-color: {palette.ring};
}}
QPushButton#IconButton:disabled {{
    background: {palette.panel};
    border: {BORDER_WIDTH_PX}px solid {palette.danger};
}}
QListWidget {{
    background: {palette.panel};
    border: {THIN_BORDER_WIDTH_PX}px solid transparent;
    border-radius: {RADIUS_PX}px;
    padding: 4px;
}}
QListWidget::item {{
    padding: 6px 8px;
    border-radius: {RADIUS_PX}px;
}}
QListWidget::item:selected {{
    background: {palette.accent};
    color: {palette.selection_text};
}}
QTextBrowser {{
    background: {palette.panel};
    color: {palette.text};
    border: {BORDER_WIDTH_PX}px solid transparent;
    border-radius: {RADIUS_PX}px;
    padding: 10px;
}}
QTextBrowser:enabled:focus {{
    border-color: {palette.ring};
}}
QLabel {{
    background: transparent;
    color: {palette.text};
}}
QLabel#Muted {{
    color: {palette.muted};
}}
QToolTip {{
    background: {palette.control};
    color: {palette.text};
    border: {THIN_BORDER_WIDTH_PX}px solid {palette.muted};
    padding: 4px;
}}
QScrollBar:vertical {{
    background: {palette.panel};
    width: 12px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {palette.control};
    border-radius: {RADIUS_PX}px;
    min-height: 24px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}
"""


def document_style(palette: Palette) -> str:
    """The style sheet applied to rendered skill documents."""
    return f"""
body {{ color: {palette.text}; }}
h1, h2, h3 {{ color: {palette.accent}; }}
a {{ color: {palette.ring}; }}
code, pre {{ background: {palette.code_background}; }}
th {{ color: {palette.muted}; }}
"""
