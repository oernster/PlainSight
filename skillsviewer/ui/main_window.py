"""The window: two trays around the library and a reading pane."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QEvent, Qt
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QMainWindow,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from .. import version
from ..application.ports import AssetLocator, MarkdownRenderer
from ..application.services import SkillLibraryService
from ..application.update import UpdateService
from ..domain.settings import Appearance, EditorChoice, FontSize
from ..domain.skill import Skill
from .about_dialog import AboutDialog
from .bottom_tray import BottomTray
from .keyboard_nav import KeyboardNavigator, NeutralStart
from .licence_dialog import LicenceDialog
from .skill_tree import SkillTree
from .skill_view import SkillView
from .theme import Palette, palette_for, stylesheet
from .top_tray import TopTray
from .update_check import install_update_check

WINDOW_WIDTH_PX = 1100
WINDOW_HEIGHT_PX = 760
TREE_WIDTH_PX = 280
STATUS_TIMEOUT_MS = 6000

UI_LICENCE_TITLE = "User interface licence (LGPL-3.0)"
MODEL_LICENCE_TITLE = "Model licence (GPL-3.0)"
UI_LICENCE_FILE = "LICENSE-LGPL-3.0.txt"
MODEL_LICENCE_FILE = "LICENSE-GPL-3.0.txt"
FALLBACK_LICENCE_FILE = "LICENSE"

FOLDER_PROMPT = "Choose the folder your skills live in"
EDITOR_PROMPT = "Choose the editor to open a skill in"
NO_EDITOR_MESSAGE = "Could not start the editor"
NO_BROWSER_MESSAGE = "Could not open a browser for the donation page"


class MainWindow(QMainWindow):
    """Everything the user sees, wired to the service and nothing else."""

    def __init__(
        self,
        service: SkillLibraryService,
        renderer: MarkdownRenderer,
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
        self.skill_tree = SkillTree(self._palette, service.opened_groups(), self)
        self.skill_view = SkillView(renderer, self._palette, self)
        self.skill_tree.skill_selected.connect(self.show_skill)
        self.skill_tree.groups_changed.connect(self.remember_groups)

        self._neutral = NeutralStart(self)
        self._started = False
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
        self.skill_view.remember_place()
        application = QApplication.instance()
        if application is not None:
            application.setStyleSheet(stylesheet(self._palette, self._font_size))
        self.top_tray.face_appearance(self._appearance())
        self.top_tray.face_font_size(self._font_size)
        self.skill_tree.wear(self._palette)
        self.skill_view.wear(self._palette)
        self.show_skill(self.skill_tree.selected_skill())

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
        splitter.addWidget(self.skill_tree)
        splitter.addWidget(self.skill_view)
        splitter.setStretchFactor(1, 1)
        self.skill_tree.setMinimumWidth(TREE_WIDTH_PX)

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
        self.skill_view.sync_focus_policy()
        return (
            *self.top_tray.ring_stops(),
            self.skill_tree,
            self.skill_view,
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

        Design plan 12.1. A user who leaves to edit a skill and comes back sees
        current content, with no watcher and no polling thread.
        """
        super().changeEvent(event)
        if event.type() is QEvent.Type.ActivationChange and self.isActiveWindow():
            self.refresh()

    def refresh(self) -> None:
        """Read the current root and show what it holds."""
        catalogue = self._service.load()
        self.skill_tree.show_catalogue(catalogue)
        if catalogue.is_empty:
            self.skill_view.show_empty_root()
        self.sync_editor_button()

    def show_skill(self, skill: Skill | None) -> None:
        """Render the selected skill; say so when none is selected."""
        if skill is None:
            self.skill_view.show_nothing()
        else:
            self.skill_view.show_skill(skill)
        self.sync_editor_button()

    def remember_groups(self, opened: tuple[str, ...]) -> None:
        """Carry the reader's open and shut groups into the next run.

        Routed through the window rather than connected straight to the
        service: the service is a frozen object with slots, which Qt cannot
        take the weak reference to that a bound method connection needs.
        """
        self._service.remember_opened_groups(opened)

    def sync_editor_button(self) -> None:
        """Ask the service whether the view in editor control can act."""
        selected = self.skill_tree.selected_skill()
        self.top_tray.open_in_editor_button.setEnabled(
            self._service.can_open_in_editor(selected)
        )

    def choose_folder(self) -> None:
        """Browse to a different skills folder and read it."""
        chosen = QFileDialog.getExistingDirectory(
            self, FOLDER_PROMPT, self._service.current_root()
        )
        if not chosen:
            return
        self.skill_tree.show_catalogue(self._service.choose_root(chosen))
        self.sync_editor_button()

    def choose_editor(self) -> None:
        """Pick the editor a skill opens in."""
        chosen, _filter = QFileDialog.getOpenFileName(self, EDITOR_PROMPT)
        if not chosen:
            return
        self._service.choose_editor(
            EditorChoice(path=chosen, display_name=Path(chosen).name)
        )
        self.sync_editor_button()

    def open_in_editor(self) -> None:
        """Hand the selected skill's document to the chosen editor."""
        skill = self.skill_tree.selected_skill()
        if skill is None:
            return
        if not self._service.open_in_editor(skill):
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
        AboutDialog(self._palette, self._assets, self).exec()

    def show_ui_licence(self) -> None:
        """Open the user interface licence."""
        self._show_licence(UI_LICENCE_TITLE, UI_LICENCE_FILE)

    def show_model_licence(self) -> None:
        """Open the model licence."""
        self._show_licence(MODEL_LICENCE_TITLE, MODEL_LICENCE_FILE)

    def _show_licence(self, title: str, file_name: str) -> None:
        LicenceDialog(title, find_licence(file_name), self).exec()


def find_licence(file_name: str) -> Path | None:
    """A licence file at the repository root; the single LICENSE as fallback."""
    root = Path(__file__).resolve().parent.parent.parent
    for candidate in (root / file_name, root / FALLBACK_LICENCE_FILE):
        if candidate.is_file():
            return candidate
    return None
