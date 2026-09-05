"""The library: one ring stop, walked with Up and Down.

The tree mirrors the folders on disk. A root is a row, the folders beneath it
are rows under that, then a document is a leaf carrying the file's own name,
so a reader who finds something here can find the same thing in a file
dialogue.

Nothing is selected until the reader selects it. A tree that opened on its
first document would start reading a file nobody asked for; the pane reads
itself down the page, so the application would be scrolling through somebody
else's document before they had touched anything.

The arrow is drawn at runtime in the palette's own colour rather than styled or
written as a character. Qt renders a stylesheet triangle as nothing at all and
draws a branch arrow only from an image file; a text glyph would depend on a
font holding it, which could not be verified in this harness. A drawn shape has
neither problem and follows the theme by construction.
"""

from __future__ import annotations

from PySide6.QtCore import QPointF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QIcon, QKeyEvent, QPainter, QPixmap, QPolygonF
from PySide6.QtWidgets import QTreeWidget, QTreeWidgetItem, QWidget

from ..domain.document import Document
from ..domain.library import Folder, Library
from .theme import Palette

DOCUMENT_ROLE = int(Qt.ItemDataRole.UserRole)
FOLDER_ROLE = int(Qt.ItemDataRole.UserRole) + 1
UNREADABLE_SUFFIX = " (unreadable)"
TOGGLE_KEYS = (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space)
FIRST_COLUMN = 0
# Twice the size it began at: at half this the triangle read as a speck
# rather than as the control it is.
ARROW_PX = 24
COUNT_OPENER = " ("

SHUT_POINTS = ((0.30, 0.15), (0.75, 0.50), (0.30, 0.85))
OPEN_POINTS = ((0.15, 0.32), (0.85, 0.32), (0.50, 0.78))


class LibraryTree(QTreeWidget):
    """Every document in the current library, under the folders holding it."""

    document_selected = Signal(object)
    folders_changed = Signal(tuple)

    def __init__(
        self,
        palette: Palette,
        opened: tuple[str, ...] = (),
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("LibraryTree")
        self.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        # One stop, not one per cell: Tab must leave the tree in a single press.
        self.setTabKeyNavigation(False)
        self.setHeaderHidden(True)
        self.setColumnCount(1)
        # The arrow is the folder's own icon, so the branch column stays bare.
        self.setRootIsDecorated(False)
        self.setIconSize(QSize(ARROW_PX, ARROW_PX))
        self._palette = palette
        self._selected: Document | None = None
        # What is open is remembered rather than what is shut, so a library
        # opens with every folder closed until the reader opens one.
        self._opened: set[str] = set(opened)
        self.currentItemChanged.connect(self._announce)
        self.itemExpanded.connect(self._remember_open)
        self.itemCollapsed.connect(self._remember_shut)
        self.itemClicked.connect(self._toggle_folder)

    def wear(self, palette: Palette) -> None:
        """Take the colours of this palette and redraw the arrows in them."""
        self._palette = palette
        for item in self.folder_items():
            self._face(item, item.isExpanded())

    def show_library(self, library: Library) -> None:
        """Replace the rows, keeping the selected document where it survives."""
        previous = self._selected
        self.clear()
        for root in library.roots:
            self._add_folder(self, root)
        self._restore(previous)

    def selected_document(self) -> Document | None:
        """The document last chosen; None when none has been."""
        return self._selected

    def folder_items(self) -> list[QTreeWidgetItem]:
        """Every row that is a folder rather than a document, top down."""
        return [item for item in self._walk(None) if _is_folder(item)]

    def document_items(self) -> list[QTreeWidgetItem]:
        """Every row that carries a document, in the order they are drawn."""
        return [item for item in self._walk(None) if not _is_folder(item)]

    def _walk(self, parent: QTreeWidgetItem | None) -> list[QTreeWidgetItem]:
        """Every row beneath this one, in the order they are drawn."""
        found: list[QTreeWidgetItem] = []
        count = self.topLevelItemCount() if parent is None else parent.childCount()
        for row in range(count):
            item = self.topLevelItem(row) if parent is None else parent.child(row)
            found.append(item)
            found.extend(self._walk(item))
        return found

    def _add_folder(
        self, parent: QTreeWidget | QTreeWidgetItem, folder: Folder
    ) -> None:
        """One folder row, opened or closed as it was left, then its contents."""
        item = QTreeWidgetItem(parent)
        item.setText(
            FIRST_COLUMN, f"{folder.name}{COUNT_OPENER}{folder.document_count})"
        )
        item.setData(FIRST_COLUMN, FOLDER_ROLE, folder.path)
        item.setToolTip(FIRST_COLUMN, folder.path)
        for child in folder.folders:
            self._add_folder(item, child)
        for document in folder.documents:
            self._add_document(item, document)
        item.setExpanded(folder.path in self._opened)
        self._face(item, item.isExpanded())

    def _add_document(self, parent: QTreeWidgetItem, document: Document) -> None:
        item = QTreeWidgetItem(parent)
        item.setText(FIRST_COLUMN, _label(document))
        item.setData(FIRST_COLUMN, DOCUMENT_ROLE, document)
        item.setToolTip(FIRST_COLUMN, document.description or document.path)

    def _face(self, item: QTreeWidgetItem, is_open: bool) -> None:
        """Give a folder the arrow for the state it is in."""
        item.setIcon(FIRST_COLUMN, arrow_icon(self._palette.muted, is_open))

    def _restore(self, previous: Document | None) -> None:
        """Select the document that was selected; nothing otherwise.

        There is deliberately no fallback to the first row. The library is
        re-read whenever the window is activated, so a fallback would select
        something every time the reader came back from another application.
        It would also have chosen a document for them on the very first run.
        """
        self._selected = None
        if previous is None:
            return
        for item in self.document_items():
            if item.data(FIRST_COLUMN, DOCUMENT_ROLE).path == previous.path:
                self._select(item)
                return

    def _select(self, item: QTreeWidgetItem) -> None:
        """Make this the current row, unless a folder above it is shut.

        Qt opens a folder to reach a row inside it, which would undo the
        reader's own decision to close it every time the library is read again.
        A row that cannot be reached is left alone rather than dragged into
        view.
        """
        if _is_reachable(item):
            self.setCurrentItem(item)

    def _announce(
        self, current: QTreeWidgetItem | None, _previous: QTreeWidgetItem | None
    ) -> None:
        """Report a document; a folder changes nothing the reader is looking at."""
        document = (
            None if current is None else current.data(FIRST_COLUMN, DOCUMENT_ROLE)
        )
        if document is None:
            return
        self._selected = document
        self.document_selected.emit(document)

    def _remember_open(self, item: QTreeWidgetItem) -> None:
        self._opened.add(_folder_path(item))
        self._face(item, True)
        self.folders_changed.emit(tuple(sorted(self._opened)))

    def _remember_shut(self, item: QTreeWidgetItem) -> None:
        self._opened.discard(_folder_path(item))
        self._face(item, False)
        self.folders_changed.emit(tuple(sorted(self._opened)))

    def _toggle_folder(self, item: QTreeWidgetItem, _column: int) -> None:
        """A click anywhere on a folder opens or closes it.

        The whole row rather than the triangle alone: the triangle is the sign
        of what a click does, never the only part of the row that does it.
        """
        if _is_folder(item):
            item.setExpanded(not item.isExpanded())

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """Enter and Space open and close a folder.

        The horizontal arrows step the window's ring everywhere, so they cannot
        also be the tree's own open and close keys; these take their place.
        """
        current = self.currentItem()
        if current is not None and _is_folder(current) and event.key() in TOGGLE_KEYS:
            current.setExpanded(not current.isExpanded())
            event.accept()
            return
        super().keyPressEvent(event)


def arrow_icon(colour: str, is_open: bool) -> QIcon:
    """A triangle pointing down while a folder is open and right while it is shut."""
    points = OPEN_POINTS if is_open else SHUT_POINTS
    pixmap = QPixmap(ARROW_PX, ARROW_PX)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(QColor(colour))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawPolygon(
        QPolygonF([QPointF(x * ARROW_PX, y * ARROW_PX) for x, y in points])
    )
    painter.end()
    return QIcon(pixmap)


def _is_folder(item: QTreeWidgetItem) -> bool:
    """Whether this row is a folder rather than a document."""
    return item.data(FIRST_COLUMN, DOCUMENT_ROLE) is None


def _is_reachable(item: QTreeWidgetItem) -> bool:
    """Whether every folder above this row is open."""
    parent = item.parent()
    while parent is not None:
        if not parent.isExpanded():
            return False
        parent = parent.parent()
    return True


def _folder_path(item: QTreeWidgetItem) -> str:
    """The path a folder row stands for."""
    return item.data(FIRST_COLUMN, FOLDER_ROLE)


def _label(document: Document) -> str:
    """The row's text: the file's own name, then any trouble reading it."""
    name = document.name
    return name if document.is_readable else f"{name}{UNREADABLE_SUFFIX}"
