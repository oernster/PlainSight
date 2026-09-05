"""The window: two trays around the library and a reading pane."""

from __future__ import annotations

from functools import partial
from pathlib import Path

from PySide6.QtCore import QEvent, Qt
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QMainWindow,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from .. import version
from ..application.ports import AssetLocator, DocumentRenderer
from ..application.services import LibraryService
from ..application.update import UpdateService
from ..domain.document import Document
from ..domain.settings import Appearance, EditorChoice, FontSize
from . import dialogs
from .bottom_tray import BottomTray
from .document_view import DocumentView
from .keyboard_nav import KeyboardNavigator, NeutralStart
from .library_tree import LibraryTree
from .theme import Palette, palette_for, stylesheet
from .top_tray import TopTray
from .update_check import install_update_check

WINDOW_WIDTH_PX = 1100
WINDOW_HEIGHT_PX = 760
TREE_WIDTH_PX = 280
STATUS_TIMEOUT_MS = 6000

UNREADABLE_FILE_MESSAGE = "That is not a kind of document PlainSight reads"
NO_EDITOR_MESSAGE = "Could not start the editor"
NO_BROWSER_MESSAGE = "Could not open a browser for the donation page"


class MainWindow(QMainWindow):
    """Everything the user sees, wired to the service and nothing else."""

    def __init__(
        self,
        service: LibraryService,
        renderer: DocumentRenderer,
        assets: AssetLocator,
        updates: UpdateService | None = None,
    ) -> None:
        super().__init__()
        self._service = service
        self._assets = assets
        self._renderer = renderer
        self._palette: Palette = palette_for(service.appearance())
        self._font_size: FontSize = service.font_size()
        self.setWindowTitle(version.APP_NAME)
        self.resize(WINDOW_WIDTH_PX, WINDOW_HEIGHT_PX)

        self.top_tray = TopTray(
            self,
            assets,
            on_choose_folder=self.choose_folder,
            on_open_file=self.open_file,
            on_choose_editor=self.choose_editor,
            on_open_in_editor=self.open_in_editor,
            on_cycle_font_size=self.cycle_font_size,
            on_switch_appearance=self.switch_appearance,
            on_about=self.show_about,
            on_check_updates=self.check_for_updates,
        )
        self.bottom_tray = BottomTray(
            self,
            assets,
            on_donate=self.open_donation,
            on_ui_licence=self.show_ui_licence,
            on_model_licence=self.show_model_licence,
        )
        self.library_tree = LibraryTree(self._palette, service.opened_folders(), self)
        self.document_view = DocumentView(renderer, self._palette, self)
        self.library_tree.document_selected.connect(self.show_document)
        self.library_tree.folders_changed.connect(self.remember_folders)

        self._neutral = NeutralStart(self)
        self._started = False
        self._library_is_empty = True
        self.setCentralWidget(self._body())
        self.statusBar().setSizeGripEnabled(False)
        self.navigator = KeyboardNavigator(self, self.ring_stops)
        # The window works with no update check at all, which is how a test
        # gets a window that asks nothing of the network. The composition root
        # always supplies one.
        self.update_check = (
            None
            if updates is None
            else install_update_check(
                self, updates, service, version.APP_NAME, self.report_status
            )
        )
        self.apply_appearance()
        self.refresh()

    def present(self) -> None:
        """Show the window and ask for the foreground, rather than only show.

        `show` puts a window on screen and leaves where it sits to the desktop.
        Reported after a fresh install: the window opened behind everything
        else. Windows refuses the foreground to a process that does not already
        hold it unless the process that does hands the right over, which the
        setup program now does when it starts this one. Asking is this half;
        being allowed to is the other. Neither works alone.
        """
        self.show()
        self.raise_()
        self.activateWindow()

    def report_status(self, message: str) -> None:
        """Say something in the status bar for a few seconds."""
        self.statusBar().showMessage(message, STATUS_TIMEOUT_MS)

    def apply_appearance(self) -> None:
        """Repaint, re-face the toggle and re-render, in one call.

        Doing the three together is what stops a toggle showing the mode just
        departed; it is also what stops the rendered document keeping the
        colours of the palette it was rendered under.
        """
        # Before the stylesheet, because applying it reflows the page under
        # the reader; asked afterwards, the pane reports where it was thrown to.
        self.document_view.remember_place()
        application = QApplication.instance()
        if application is not None:
            application.setStyleSheet(stylesheet(self._palette, self._font_size))
        self.top_tray.face_appearance(self._appearance())
        self.top_tray.face_font_size(self._font_size)
        self.library_tree.wear(self._palette)
        self.document_view.wear(self._palette)
        self.show_document(self.library_tree.selected_document())

    def _appearance(self) -> Appearance:
        """Which appearance the current palette is."""
        return (
            Appearance.LIGHT
            if self._palette is palette_for(Appearance.LIGHT)
            else Appearance.DARK
        )

    def switch_appearance(self) -> None:
        """Move to the other appearance and remember it."""
        self._palette = palette_for(self._service.switch_appearance())
        self.apply_appearance()

    def cycle_font_size(self) -> None:
        """Step to the next text size and remember it.

        It goes through the same repaint as an appearance change, since the
        size lives in the one stylesheet and the rendered document inherits it.
        """
        self._font_size = self._service.cycle_font_size()
        self.apply_appearance()

    def _body(self) -> QWidget:
        """The central column: top tray, the split body, bottom tray."""
        splitter = QSplitter(Qt.Orientation.Horizontal, self)
        splitter.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        splitter.addWidget(self.library_tree)
        splitter.addWidget(self.document_view)
        splitter.setStretchFactor(1, 1)
        self.library_tree.setMinimumWidth(TREE_WIDTH_PX)

        middle = QHBoxLayout()
        middle.addWidget(splitter)

        central = QWidget(self)
        central.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        column = QVBoxLayout(central)
        column.addWidget(self.top_tray)
        column.addLayout(middle, 1)
        column.addWidget(self.bottom_tray)
        return central

    def ring_stops(self) -> tuple[QWidget, ...]:
        """The whole ring, in reading order, recomputed on every move.

        The reading pane appears only while it overflows: a page that fits
        scrolls nowhere, so focusing it would let the user do nothing.
        """
        self.document_view.sync_focus_policy()
        return (
            *self.top_tray.ring_stops(),
            self.library_tree,
            self.document_view,
            *self.bottom_tray.ring_stops(),
        )

    def showEvent(self, event: object) -> None:
        """Start neutral: nothing highlighted until the first Tab or Right."""
        super().showEvent(event)  # type: ignore[arg-type]
        if not self._started:
            self._started = True
            self._neutral.absorb()

    def changeEvent(self, event: QEvent) -> None:
        """Re-read the library whenever the window is activated again.

        A user who leaves to edit a document and comes back sees
        current content, with no watcher and no polling thread.
        """
        super().changeEvent(event)
        if event.type() is QEvent.Type.ActivationChange and self.isActiveWindow():
            self.refresh()

    def refresh(self) -> None:
        """Read the chosen folder and show what it holds.

        With no folder chosen nothing is read at all and the pane says so,
        which is a different statement from a folder that holds nothing.
        """
        library = self._service.load()
        self._library_is_empty = library.is_empty
        self.library_tree.show_library(library)
        self.show_document(self.library_tree.selected_document())

    def show_document(self, document: Document | None) -> None:
        """Render the selected document, else whichever message now applies.

        The body is offered as something the pane can call rather than read
        here, so a re-read that changes nothing costs no read of the file. The
        pane knows whether it is about to redraw; this does not.
        """
        if document is None:
            self._show_standing_message()
        else:
            self.document_view.show_document(
                document, partial(self._service.body_of, document)
            )
        self.sync_editor_button()

    def _show_standing_message(self) -> None:
        """What the pane says while nothing is selected.

        Three states rather than one, because they are three different facts:
        no folder has been chosen, a chosen folder holds nothing or there is
        something to read that the reader has not picked yet. Held in one
        place so a repaint or a re-read cannot leave the wrong one showing.
        """
        if not self._service.has_root():
            self.document_view.show_no_folder()
        elif self._library_is_empty:
            self.document_view.show_empty_root()
        else:
            self.document_view.show_nothing()

    def remember_folders(self, opened: tuple[str, ...]) -> None:
        """Carry the reader's open and shut folders into the next run.

        Routed through the window rather than connected straight to the
        service: the service is a frozen object with slots, which Qt cannot
        take the weak reference to that a bound method connection needs.
        """
        self._service.remember_opened_folders(opened)

    def sync_editor_button(self) -> None:
        """Ask the service whether the view in editor control can act."""
        selected = self.library_tree.selected_document()
        self.top_tray.open_in_editor_button.setEnabled(
            self._service.can_open_in_editor(selected)
        )

    def choose_folder(self) -> None:
        """Browse to a folder of documents and read it.

        The chooser opens on the last folder taken, else on the Claude skills
        folder, so the common case is one click. That is a starting place for a
        dialog the user is standing in front of; nothing is read until they
        take something.
        """
        chosen = dialogs.ask_for_folder(self, self._service.browse_from())
        if not chosen:
            return
        library = self._service.choose_root(chosen)
        self._library_is_empty = library.is_empty
        self.library_tree.show_library(library)
        self.show_document(self.library_tree.selected_document())

    def open_file(self) -> None:
        """Open one document, listing no directory around it.

        Selected as soon as it is read, which is not the auto-selection the
        tree refuses: a reader who names one file has already chosen it, where
        a reader who names a folder has not chosen anything inside it.
        """
        chosen = dialogs.ask_for_document(self, self._service.browse_from())
        if not chosen:
            return
        library = self._service.open_file(chosen)
        if library.is_empty:
            self.report_status(UNREADABLE_FILE_MESSAGE)
            return
        self._library_is_empty = False
        self.library_tree.show_library(library)
        self._select_the_only_document()

    def _select_the_only_document(self) -> None:
        """Open the one folder there is and land on the document inside it."""
        for item in self.library_tree.folder_items():
            item.setExpanded(True)
        rows = self.library_tree.document_items()
        if rows:
            self.library_tree.setCurrentItem(rows[0])

    def choose_editor(self) -> None:
        """Pick the editor a document opens in."""
        chosen = dialogs.ask_for_editor(self)
        if not chosen:
            return
        self._service.choose_editor(
            EditorChoice(path=chosen, display_name=Path(chosen).name)
        )
        self.sync_editor_button()

    def open_in_editor(self) -> None:
        """Hand the selected document to the chosen editor."""
        document = self.library_tree.selected_document()
        if document is None:
            return
        if not self._service.open_in_editor(document):
            self.report_status(NO_EDITOR_MESSAGE)

    def open_donation(self) -> None:
        """Hand the donation page to whatever the desktop opens links with.

        The application never fetches it: the address goes to the desktop and
        the browser does the asking, so nothing here opens a connection.
        """
        if not self._service.open_donation_page(version.DONATE_URL):
            self.report_status(NO_BROWSER_MESSAGE)

    def check_for_updates(self) -> None:
        """The Help menu's own check: it reports whatever it finds."""
        if self.update_check is not None:
            self.update_check.check_manually()

    def show_about(self) -> None:
        """Open the About dialog."""
        dialogs.show_about(self, self._palette, self._assets)

    def show_ui_licence(self) -> None:
        """Open the user interface licence."""
        dialogs.show_ui_licence(self)

    def show_model_licence(self) -> None:
        """Open the model licence."""
        dialogs.show_model_licence(self)
