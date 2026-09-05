"""The top tray: the two openers, the editor pair, then help at the right."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import QFrame, QHBoxLayout, QMenu, QPushButton, QWidget

from .. import version
from ..application.ports import AssetLocator
from ..domain.settings import DEFAULT_FONT_SIZE, Appearance, FontSize
from .widgets import icon_button

FOLDER_ICON = "file.png"
OPEN_FILE_ICON = "open-file.png"
CHOOSE_EDITOR_ICON = "choose-editor.png"
LAUNCH_EDITOR_ICON = "launch-editor.png"
HELP_ICON = "help-about.png"
LIGHT_MODE_ICON = "light-mode.png"
FONT_SIZE_ICONS = {
    FontSize.MEDIUM: "medium-font.png",
    FontSize.LARGE: "large-font.png",
    FontSize.EXTRA_LARGE: "extra-large-font.png",
}
DARK_MODE_ICON = "dark-mode.png"

FOLDER_TOOLTIP = "Choose the folder your documents live in"
OPEN_FILE_TOOLTIP = "Open a single document"
CHOOSE_EDITOR_TOOLTIP = "Choose the editor to open a document in"
LAUNCH_EDITOR_TOOLTIP = "Open the selected document in your editor"
HELP_TOOLTIP = "About PlainSight; check for updates"
FONT_SIZE_TOOLTIPS = {
    FontSize.MEDIUM: "Switch to medium text",
    FontSize.LARGE: "Switch to large text",
    FontSize.EXTRA_LARGE: "Switch to extra large text",
}
SEPARATOR_NAME = "TraySeparator"
SEPARATOR_WIDTH_PX = 1
SEPARATOR_MARGIN_PX = 4
TO_LIGHT_TOOLTIP = "Switch to the light appearance"
TO_DARK_TOOLTIP = "Switch to the dark appearance"

ABOUT_ITEM = f"About {version.APP_NAME}"
CHECK_UPDATES_ITEM = "Check for Updates"

TRAY_SCALE = 2.0
TRAY_MARGIN_PX = 8
TRAY_SPACING_PX = 6


class TopTray(QWidget):
    """The row of controls above the body."""

    def __init__(
        self,
        parent: QWidget | None,
        assets: AssetLocator,
        on_choose_folder: Callable[[], None],
        on_open_file: Callable[[], None],
        on_choose_editor: Callable[[], None],
        on_open_in_editor: Callable[[], None],
        on_cycle_font_size: Callable[[], None],
        on_switch_appearance: Callable[[], None],
        on_about: Callable[[], None],
        on_check_updates: Callable[[], None],
    ) -> None:
        super().__init__(parent)
        self._assets = assets
        # A container is never a stop, so it is said rather than assumed.
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.folder_button = icon_button(
            self, assets.find(FOLDER_ICON), FOLDER_TOOLTIP, on_choose_folder, TRAY_SCALE
        )
        # Immediately right of the folder button: the two are the same
        # question asked at two scales, so they sit together and ahead of
        # the editor pair, which acts on whatever they found.
        self.open_file_button = icon_button(
            self,
            assets.find(OPEN_FILE_ICON),
            OPEN_FILE_TOOLTIP,
            on_open_file,
            TRAY_SCALE,
        )
        self.choose_editor_button = icon_button(
            self,
            assets.find(CHOOSE_EDITOR_ICON),
            CHOOSE_EDITOR_TOOLTIP,
            on_choose_editor,
            TRAY_SCALE,
        )
        self.open_in_editor_button = icon_button(
            self,
            assets.find(LAUNCH_EDITOR_ICON),
            LAUNCH_EDITOR_TOOLTIP,
            on_open_in_editor,
            TRAY_SCALE,
        )
        # Disabled by default, per design plan 7.3. The ring skips it and it
        # paints the permanent red ring while it stays that way.
        self.open_in_editor_button.setEnabled(False)
        # It wears the size it would move TO, exactly as the appearance toggle
        # does, so the picture always answers "what happens if I press this".
        self.font_size_button = icon_button(
            self,
            assets.find(FONT_SIZE_ICONS[DEFAULT_FONT_SIZE.next_in_cycle]),
            FONT_SIZE_TOOLTIPS[DEFAULT_FONT_SIZE.next_in_cycle],
            on_cycle_font_size,
            TRAY_SCALE,
        )
        self.separator = _separator(self)
        # It shows the appearance it would move TO, so the sun appears while
        # you are in the dark.
        self.appearance_button = icon_button(
            self,
            assets.find(LIGHT_MODE_ICON),
            TO_LIGHT_TOOLTIP,
            on_switch_appearance,
            TRAY_SCALE,
        )
        self.help_button = icon_button(
            self, assets.find(HELP_ICON), HELP_TOOLTIP, self.show_help_menu, TRAY_SCALE
        )
        # Built here rather than on each press, so the same menu is shown every
        # time and the button owns it for as long as the button lives.
        self.help_menu = QMenu(self.help_button)
        self.about_action = self.help_menu.addAction(ABOUT_ITEM)
        self.about_action.triggered.connect(on_about)
        self.check_updates_action = self.help_menu.addAction(CHECK_UPDATES_ITEM)
        self.check_updates_action.triggered.connect(on_check_updates)

        row = QHBoxLayout(self)
        row.setContentsMargins(
            TRAY_MARGIN_PX, TRAY_MARGIN_PX, TRAY_MARGIN_PX, TRAY_MARGIN_PX
        )
        row.setSpacing(TRAY_SPACING_PX)
        row.addWidget(self.folder_button)
        row.addWidget(self.open_file_button)
        row.addWidget(self.choose_editor_button)
        row.addWidget(self.open_in_editor_button)
        row.addWidget(self.separator)
        row.addWidget(self.font_size_button)
        row.addStretch()
        row.addWidget(self.appearance_button)
        row.addWidget(self.help_button)

    def show_help_menu(self) -> None:
        """Drop the menu under the button rather than beside the pointer.

        Popped by hand instead of set on the button, because a button carrying
        a menu grows an arrow indicator; every other control in this tray is a
        picture and nothing else.
        """
        below = self.help_button.rect().bottomLeft()
        self.help_menu.popup(self.help_button.mapToGlobal(below))

    def ring_stops(self) -> tuple[QPushButton, ...]:
        """This tray's controls, left to right as they are drawn."""
        return (
            self.folder_button,
            self.open_file_button,
            self.choose_editor_button,
            self.open_in_editor_button,
            self.font_size_button,
            self.appearance_button,
            self.help_button,
        )

    def face_font_size(self, size: FontSize) -> None:
        """Wear the size the button would move to, never the current one."""
        moving_to = size.next_in_cycle
        self._wear(
            self.font_size_button,
            FONT_SIZE_ICONS[moving_to],
            FONT_SIZE_TOOLTIPS[moving_to],
        )

    def face_appearance(self, appearance: Appearance) -> None:
        """Wear the appearance the toggle would move to, never the current one.

        Re-facing happens in the same call as the repaint, so a toggle can never
        be left showing the mode just departed and invite a second press.
        """
        moving_to_light = appearance is Appearance.DARK
        icon = LIGHT_MODE_ICON if moving_to_light else DARK_MODE_ICON
        tooltip = TO_LIGHT_TOOLTIP if moving_to_light else TO_DARK_TOOLTIP
        self._wear(self.appearance_button, icon, tooltip)

    def _wear(self, button: QPushButton, icon: str, tooltip: str) -> None:
        """Put this picture and this wording on a button that steps a cycle."""
        found = self._assets.find(icon)
        if found is not None:
            button.setIcon(QIcon(QPixmap(found)))
        button.setToolTip(tooltip)
        button.setAccessibleName(tooltip)


def _separator(parent: QWidget) -> QFrame:
    """A hairline between the editor controls and the text size control.

    A container is never a focus stop, so it is said rather than assumed.
    """
    line = QFrame(parent)
    line.setObjectName(SEPARATOR_NAME)
    line.setFrameShape(QFrame.Shape.VLine)
    line.setFrameShadow(QFrame.Shadow.Plain)
    line.setFixedWidth(SEPARATOR_WIDTH_PX)
    line.setContentsMargins(
        SEPARATOR_MARGIN_PX,
        SEPARATOR_MARGIN_PX,
        SEPARATOR_MARGIN_PX,
        SEPARATOR_MARGIN_PX,
    )
    line.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    return line
