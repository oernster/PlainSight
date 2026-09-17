"""The count at the right of the status bar: how long the document is.

It sits as a permanent widget rather than as a message, so the transient
things the status bar says (an editor that would not start, an update that was
looked for) pass across the left of the same strip without displacing it.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QWidget

from ..domain.extent import Extent

MUTED_NAME = "Muted"
NOTHING_TO_SAY = ""
READOUT = "length: {characters:,}    lines: {lines:,}"
TOOLTIP = "Characters and lines of the text being read"
# The status bar leaves a permanent widget almost against the window frame,
# which reads as though the count had been cut off.
RIGHT_GAP_PX = 8


class ExtentReadout(QLabel):
    """How much text the open document holds, counted in both ways."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName(MUTED_NAME)
        # A readout is not a control: it takes no focus and no ring.
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setToolTip(TOOLTIP)
        self.setContentsMargins(0, 0, RIGHT_GAP_PX, 0)
        self.show_extent(None)

    def show_extent(self, extent: Extent | None) -> None:
        """Report this extent; say nothing at all when there is none.

        Nothing rather than zeroes, because they are different statements.
        Either no document is open or the one that is could not be read, so
        there is no text to have a length; a count of nought would claim a
        document that holds nothing, which is a thing a file can be.
        """
        self.setText(NOTHING_TO_SAY if extent is None else _worded(extent))


def _worded(extent: Extent) -> str:
    """The extent as the status bar says it, grouped for reading at a glance."""
    return READOUT.format(characters=extent.characters, lines=extent.lines)
