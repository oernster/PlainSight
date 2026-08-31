"""No pane is a stop and no pane paints a ring.

Two checks, because neither alone is enough: the stylesheet cannot name a
container as a ring selector, then no container appears in the toolkit's own
focus chain. The chain walk is the trustworthy headless measurement, since it is
structure rather than paint.
"""

from __future__ import annotations

import re

from PySide6.QtWidgets import (
    QAbstractScrollArea,
    QFrame,
    QGroupBox,
    QScrollArea,
    QSplitter,
    QStackedWidget,
    QWidget,
)

from skillsviewer.infrastructure.resources import BundledAssets
from skillsviewer.ui.about_dialog import AboutDialog
from skillsviewer.ui.licence_dialog import LicenceDialog
from skillsviewer.ui.main_window import MainWindow
from skillsviewer.ui.theme import DARK, stylesheet

CONTAINER_SELECTORS = (
    "*",
    "QWidget",
    "QFrame",
    "QAbstractScrollArea",
    "QScrollArea",
    "QGroupBox",
    "QStackedWidget",
    "QSplitter",
    "QTabWidget",
)

# The reading pane is the one sanctioned exception, scoped to an object name so
# it cannot reach a subclass; focus only rather than hover.
SANCTIONED = ("QTextBrowser:enabled:focus",)

CONTAINER_TYPES = (QScrollArea, QSplitter, QStackedWidget, QGroupBox)
RING_PROPERTY = re.compile(r"border(-color)?\s*:")
ITEM_VIEW_HOVER = re.compile(r"QListWidget[^{,]*:hover")


def rules(sheet: str) -> list[tuple[str, str]]:
    """Every selector and its block, as written."""
    return [
        (match.group(1).strip(), match.group(2))
        for match in re.finditer(r"([^{}]+)\{([^}]*)\}", sheet)
    ]


def test_no_container_class_carries_a_ring_rule() -> None:
    offences = []
    for selector, block in rules(stylesheet(DARK)):
        if selector in SANCTIONED or not RING_PROPERTY.search(block):
            continue
        if ":hover" not in selector and ":focus" not in selector:
            continue
        for container in CONTAINER_SELECTORS:
            if re.search(rf"(^|[\s,]){re.escape(container)}[:\s,]", selector + " "):
                offences.append(selector)

    assert offences == []


def test_the_item_view_takes_no_hover_ring() -> None:
    assert ITEM_VIEW_HOVER.search(stylesheet(DARK)) is None


def test_the_item_view_takes_no_focus_ring_either() -> None:
    """Its current row is the indicator, so a rectangle round it is noise."""
    offences = [
        selector
        for selector, block in rules(stylesheet(DARK))
        if "QListWidget" in selector
        and ":focus" in selector
        and RING_PROPERTY.search(block)
    ]

    assert offences == []


def chain_offences(root: QWidget) -> list[str]:
    """Every container the toolkit's own focus chain would reach."""
    found: list[str] = []
    widget = root.nextInFocusChain()
    seen: set[int] = set()
    while widget is not None and id(widget) not in seen:
        seen.add(id(widget))
        if _is_container_stop(widget, root):
            found.append(type(widget).__name__)
        widget = widget.nextInFocusChain()
    return found


def _is_container_stop(widget: QWidget, root: QWidget) -> bool:
    from PySide6.QtCore import Qt

    if not root.isAncestorOf(widget):
        return False
    if not bool(widget.focusPolicy() & Qt.FocusPolicy.TabFocus):
        return False
    if isinstance(widget, CONTAINER_TYPES):
        return True
    is_bare_container = type(widget) in (QWidget, QFrame)
    scroll_area = isinstance(widget, QAbstractScrollArea)
    return is_bare_container and not scroll_area


def test_no_container_is_in_the_main_window_focus_chain(window: MainWindow) -> None:
    offences = [name for name in chain_offences(window) if name != "NeutralStart"]

    assert offences == []


def test_no_container_is_in_a_dialog_focus_chain(window: MainWindow) -> None:
    for dialog in (
        AboutDialog(DARK, BundledAssets(), window),
        LicenceDialog("A licence", None, window),
    ):
        dialog.show()
        assert chain_offences(dialog) == []
        dialog.close()
