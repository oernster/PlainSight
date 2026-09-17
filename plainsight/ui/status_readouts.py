"""What the status bar says about the document being read, at either end.

Two standing statements rather than one, because they are known at different
moments and from different things. The kind is known from the file name, so a
document that cannot be read still has one; the length needs the text, so a
document that cannot be read has none.

The kind sits at the left as an ordinary widget, which is the end the status
bar hands to whatever it is saying at the time: an editor that would not start
covers it for a few seconds and it returns. The length sits at the right as a
permanent one, where nothing transient reaches it.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QWidget

from ..domain.document import DocumentKind
from ..domain.extent import Extent

MUTED_NAME = "Muted"
NOTHING_TO_SAY = ""
READOUT = "length: {characters:,}    lines: {lines:,}"
EXTENT_TOOLTIP = "Characters and lines of the text being read"
KIND_TOOLTIP = "What kind of document this is"
# The status bar leaves a readout almost against the window frame, which reads
# as though it had been cut off. The gap is on the outer side of each; the
# inner side needs none, since the stylesheet takes the divider the style
# would otherwise draw at an item's far edge, measured landing against the
# last letter and reading as a text cursor sitting there.
GAP_PX = 8
AT_THE_LEFT = (GAP_PX, 0, 0, 0)
AT_THE_RIGHT = (0, 0, GAP_PX, 0)


class StatusReadout(QLabel):
    """One standing statement in the status bar: words, else nothing at all."""

    def __init__(
        self,
        tooltip: str,
        margins: tuple[int, int, int, int],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName(MUTED_NAME)
        # A readout is not a control: it takes no focus and no ring.
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setToolTip(tooltip)
        self.setContentsMargins(*margins)
        self.say(None)

    def say(self, words: str | None) -> None:
        """Report this; say nothing at all where there is nothing to report."""
        self.setText(NOTHING_TO_SAY if words is None else words)


class KindReadout(StatusReadout):
    """What kind of document is open, at the left of the status bar."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(KIND_TOOLTIP, AT_THE_LEFT, parent)

    def show_kind(self, kind: DocumentKind | None) -> None:
        """Name this kind; say nothing while no document is open.

        A document that could not be read still has a kind, since the kind
        comes from the file name rather than from anything inside the file.
        """
        self.say(None if kind is None else kind.display_name)


class ExtentReadout(StatusReadout):
    """How much text the open document holds, at the right of the status bar."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(EXTENT_TOOLTIP, AT_THE_RIGHT, parent)

    def show_extent(self, extent: Extent | None) -> None:
        """Report this extent; say nothing at all when there is none.

        Nothing rather than zeroes, because they are different statements.
        Either no document is open or the one that is could not be read, so
        there is no text to have a length; a count of nought would claim a
        document that holds nothing, which is a thing a file can be.
        """
        self.say(None if extent is None else _worded(extent))


def _worded(extent: Extent) -> str:
    """The extent as the status bar says it, grouped for reading at a glance."""
    return READOUT.format(characters=extent.characters, lines=extent.lines)
