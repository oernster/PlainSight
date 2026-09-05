"""The small pieces the trays and dialogs are built from."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import QDialog, QHBoxLayout, QPushButton, QWidget

ICON_BUTTON_NAME = "IconButton"
ICON_SIZE_PX = 28
BUTTON_SIZE_PX = 40
CLOSE_LABEL = "Close"


def icon_button(
    parent: QWidget,
    artwork: str | None,
    tooltip: str,
    on_press: Callable[[], None],
    scale: float = 1.0,
) -> QPushButton:
    """A picture button, sized the same as every other one in its own tray.

    The scale belongs to the tray rather than to the button: the two trays are
    read at different distances and carry different weight, so they are sized
    apart on purpose rather than sharing one figure.
    """
    button = QPushButton(parent)
    button.setObjectName(ICON_BUTTON_NAME)
    button.setToolTip(tooltip)
    button.setAccessibleName(tooltip)
    button.setFixedSize(round(BUTTON_SIZE_PX * scale), round(BUTTON_SIZE_PX * scale))
    button.setIconSize(QSize(round(ICON_SIZE_PX * scale), round(ICON_SIZE_PX * scale)))
    button.setFocusPolicy(Qt.FocusPolicy.TabFocus)
    if artwork is not None:
        button.setIcon(QIcon(QPixmap(artwork)))
    button.clicked.connect(on_press)
    return button


def close_row(dialog: QDialog) -> QHBoxLayout:
    """The row every dialog ends with: a stretch, then Close."""
    row = QHBoxLayout()
    row.addStretch()
    button = QPushButton(CLOSE_LABEL, dialog)
    button.setFocusPolicy(Qt.FocusPolicy.TabFocus)
    button.clicked.connect(dialog.accept)
    row.addWidget(button)
    return row


class FirstStopDialog(QDialog):
    """A dialog that opens already focused on its first usable control.

    The opposite of the main window's neutral start, deliberately so: the dialog
    was opened to do one thing, so making the user press Tab first costs a
    keystroke and tells them nothing.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        # Closed means gone. Parented to the window and merely hidden, every
        # dialog ever opened stayed alive with its reading cycle still ticking:
        # ten openings of a licence measured as ten dialogs and ten timers.
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self._entered = False

    def showEvent(self, event: object) -> None:
        super().showEvent(event)  # type: ignore[arg-type]
        if self._entered:
            return
        self._entered = True
        stop = self.first_stop()
        if stop is not None:
            stop.setFocus(Qt.FocusReason.TabFocusReason)

    def first_stop(self) -> QWidget | None:
        """The first control the dialog's own tab order would reach."""
        widget = self.nextInFocusChain()
        seen: set[int] = set()
        while widget is not None and id(widget) not in seen:
            seen.add(id(widget))
            reachable = (
                widget is not self
                and self.isAncestorOf(widget)
                and widget.isEnabled()
                and widget.isVisible()
                and bool(widget.focusPolicy() & Qt.FocusPolicy.TabFocus)
            )
            if reachable:
                return widget
            widget = widget.nextInFocusChain()
        return None


def make_pane(parent: QWidget | None = None) -> QWidget:
    """A container, said to be no focus stop rather than assumed to be none."""
    pane = QWidget(parent)
    pane.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    return pane
