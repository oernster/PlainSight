"""One home for every colour value, plus the stylesheet built from them.

The ring model has exactly three states: nothing at rest, green while a control
is hovered or focused and enabled, permanent red while it is disabled. The
accent is never a ring; it carries meaning only.

A ring belongs to a control, never to a region that holds text. Neither the
skill tree nor the reading pane paints one in any state.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..domain.settings import DEFAULT_FONT_SIZE, Appearance, FontSize

# The three text sizes, derived from one base and one step rather than written
# out separately, so they cannot drift apart. The rendered document sets no size
# of its own, so it inherits this and scales with everything else.
BASE_FONT_PX = 14
FONT_STEP_PX = 3
FONT_SIZE_PX = {
    FontSize.MEDIUM: BASE_FONT_PX,
    FontSize.LARGE: BASE_FONT_PX + FONT_STEP_PX,
    FontSize.EXTRA_LARGE: BASE_FONT_PX + FONT_STEP_PX + FONT_STEP_PX,
}

BORDER_WIDTH_PX = 2
THIN_BORDER_WIDTH_PX = 1
RADIUS_PX = 6
LINE_HEIGHT_PERCENT = 155
PARAGRAPH_GAP_PX = 10
ITEM_GAP_PX = 6
HEADING_GAP_PX = 20


@dataclass(frozen=True, slots=True)
class Palette:
    """Every colour the application draws with."""

    window: str
    panel: str
    control: str
    text: str
    muted: str
    accent: str
    selection: str
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
    accent="#a78bfa",
    selection="#4c2a9e",
    ring="#22c55e",
    danger="#ef4444",
    selection_text="#ffffff",
    code_background="#0e1117",
)

# The ring and danger tokens are per theme rather than shared. A pastel green
# that reads on near-black is weak on white, so light names a saturated one of
# its own; the same goes for the red.
#
# The dark theme carries a separate selection fill because one accent cannot do
# both of its jobs there. A heading drawn on the panel wants a lighter violet
# and white drawn on the selected row wants a darker one; asking a single token
# for both left the headings at 4.14 to 1 and the selected row at 3.99, each
# under the 4.5 that is readable. The light theme has no such tension, so its
# two are the same value and stay so honestly rather than by coincidence.
LIGHT = Palette(
    window="#f5f6fa",
    panel="#ffffff",
    control="#eceef5",
    text="#161a22",
    muted="#5b6478",
    accent="#5a49d6",
    selection="#5a49d6",
    ring="#047857",
    danger="#b91c1c",
    selection_text="#ffffff",
    code_background="#eef0f6",
)


def palette_for(appearance: Appearance) -> Palette:
    """The palette this appearance draws with."""
    return LIGHT if appearance is Appearance.LIGHT else DARK


def stylesheet(palette: Palette, font_size: FontSize = DEFAULT_FONT_SIZE) -> str:
    """The application stylesheet, built from one palette and one text size.

    A container class never appears in a ring rule. The skill tree is an item
    view, so it takes no ring in any state: its current row is the indicator.
    The reading pane takes none either. It is a region the pointer rests
    inside rather than a control it points at, so a rectangle round the words
    being read reports where the mouse is and marks no target; clicking the
    text to use the document keys drew it every time. The group arrows are
    drawn rather than styled, since Qt renders a stylesheet triangle as
    nothing at all.
    """
    return f"""
* {{
    outline: none;
}}
QWidget {{
    background: {palette.window};
    color: {palette.text};
    font-size: {FONT_SIZE_PX[font_size]}px;
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
QFrame#TraySeparator {{
    background: {palette.control};
    border: none;
}}
QMenu {{
    background: {palette.panel};
    color: {palette.text};
    border: {THIN_BORDER_WIDTH_PX}px solid {palette.control};
    border-radius: {RADIUS_PX}px;
    padding: 4px;
}}
QMenu::item {{
    padding: 6px 16px;
    border-radius: {RADIUS_PX}px;
}}
QMenu::item:selected {{
    background: {palette.selection};
    color: {palette.selection_text};
}}
QTreeWidget {{
    background: {palette.panel};
    border: {THIN_BORDER_WIDTH_PX}px solid transparent;
    border-radius: {RADIUS_PX}px;
    padding: 4px;
}}
QTreeWidget::item {{
    padding: 6px 8px;
    border-radius: {RADIUS_PX}px;
}}
QTreeWidget::item:selected {{
    background: {palette.selection};
    color: {palette.selection_text};
}}
QTextBrowser {{
    background: {palette.panel};
    color: {palette.text};
    border: {BORDER_WIDTH_PX}px solid transparent;
    border-radius: {RADIUS_PX}px;
    padding: 10px;
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
    """The style sheet applied to rendered documents.

    The typography is here because a skill's own paragraphs can be enormous:
    the longest measured runs past four thousand characters unbroken. Nothing
    here may rewrite what an author wrote, so the levers are the ones a reader
    owns, open line spacing and air between blocks, with the line length
    capped by the pane itself.
    """
    return f"""
body {{ color: {palette.text}; }}
p, li, td, th {{ line-height: {LINE_HEIGHT_PERCENT}%; }}
p {{ margin-top: {PARAGRAPH_GAP_PX}px; margin-bottom: {PARAGRAPH_GAP_PX}px; }}
li {{ margin-top: {ITEM_GAP_PX}px; margin-bottom: {ITEM_GAP_PX}px; }}
h1, h2, h3 {{
    color: {palette.accent};
    margin-top: {HEADING_GAP_PX}px;
    margin-bottom: {ITEM_GAP_PX}px;
}}
a {{ color: {palette.ring}; }}
code, pre {{ background: {palette.code_background}; }}
th {{ color: {palette.muted}; }}
"""
