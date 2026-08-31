"""The top tray: the folder, the editor pair, then help at the far right."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QPushButton, QWidget

from ..application.ports import AssetLocator
from .widgets import icon_button

FOLDER_ICON = "file.png"
CHOOSE_EDITOR_ICON = "choose-editor.png"
LAUNCH_EDITOR_ICON = "launch-editor.png"
HELP_ICON = "help-about.png"

FOLDER_TOOLTIP = "Choose the folder your skills live in"
CHOOSE_EDITOR_TOOLTIP = "Choose the editor to open a skill in"
LAUNCH_EDITOR_TOOLTIP = "Open the selected skill in your editor"
HELP_TOOLTIP = "About Skills Viewer"

TRAY_MARGIN_PX = 8
TRAY_SPACING_PX = 6


class TopTray(QWidget):
    """The row of controls above the body."""

    def __init__(
        self,
        parent: QWidget | None,
        assets: AssetLocator,
        on_choose_folder: Callable[[], None],
        on_choose_editor: Callable[[], None],
        on_open_in_editor: Callable[[], None],
        on_help: Callable[[], None],
    ) -> None:
        super().__init__(parent)
        # A container is never a stop, so it is said rather than assumed.
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.folder_button = icon_button(
            self, assets.find(FOLDER_ICON), FOLDER_TOOLTIP, on_choose_folder
        )
        self.choose_editor_button = icon_button(
            self,
            assets.find(CHOOSE_EDITOR_ICON),
            CHOOSE_EDITOR_TOOLTIP,
            on_choose_editor,
        )
        self.open_in_editor_button = icon_button(
            self,
            assets.find(LAUNCH_EDITOR_ICON),
            LAUNCH_EDITOR_TOOLTIP,
            on_open_in_editor,
        )
        # Disabled by default, per design plan 7.3. The ring skips it and it
        # paints the permanent red ring while it stays that way.
        self.open_in_editor_button.setEnabled(False)
        self.help_button = icon_button(
            self, assets.find(HELP_ICON), HELP_TOOLTIP, on_help
        )

        row = QHBoxLayout(self)
        row.setContentsMargins(
            TRAY_MARGIN_PX, TRAY_MARGIN_PX, TRAY_MARGIN_PX, TRAY_MARGIN_PX
        )
        row.setSpacing(TRAY_SPACING_PX)
        row.addWidget(self.folder_button)
        row.addWidget(self.choose_editor_button)
        row.addWidget(self.open_in_editor_button)
        row.addStretch()
        row.addWidget(self.help_button)

    def ring_stops(self) -> tuple[QPushButton, ...]:
        """This tray's controls, left to right as they are drawn."""
        return (
            self.folder_button,
            self.choose_editor_button,
            self.open_in_editor_button,
            self.help_button,
        )
