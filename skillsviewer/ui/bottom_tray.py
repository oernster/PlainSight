"""The bottom tray: donate at the far left, then the two licences."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QPushButton, QWidget

from ..application.ports import AssetLocator
from .widgets import icon_button

DONATE_ICON = "donate.png"
UI_LICENCE_ICON = "ui-licence.png"
MODEL_LICENCE_ICON = "model-licence.png"

DONATE_TOOLTIP = "Buy the author a drink (opens your browser)"
UI_LICENCE_TOOLTIP = "The user interface licence (LGPL-3.0)"
MODEL_LICENCE_TOOLTIP = "The model licence (GPL-3.0)"

TRAY_MARGIN_PX = 8
TRAY_SPACING_PX = 6


class BottomTray(QWidget):
    """The row of controls beneath the body."""

    def __init__(
        self,
        parent: QWidget | None,
        assets: AssetLocator,
        on_donate: Callable[[], None],
        on_ui_licence: Callable[[], None],
        on_model_licence: Callable[[], None],
    ) -> None:
        super().__init__(parent)
        # A container is never a stop, so it is said rather than assumed.
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.donate_button = icon_button(
            self, assets.find(DONATE_ICON), DONATE_TOOLTIP, on_donate
        )
        self.ui_licence_button = icon_button(
            self,
            assets.find(UI_LICENCE_ICON),
            UI_LICENCE_TOOLTIP,
            on_ui_licence,
        )
        self.model_licence_button = icon_button(
            self,
            assets.find(MODEL_LICENCE_ICON),
            MODEL_LICENCE_TOOLTIP,
            on_model_licence,
        )

        row = QHBoxLayout(self)
        row.setContentsMargins(
            TRAY_MARGIN_PX, TRAY_MARGIN_PX, TRAY_MARGIN_PX, TRAY_MARGIN_PX
        )
        row.setSpacing(TRAY_SPACING_PX)
        row.addWidget(self.donate_button)
        row.addWidget(self.ui_licence_button)
        row.addWidget(self.model_licence_button)
        row.addStretch()

    def ring_stops(self) -> tuple[QPushButton, ...]:
        """This tray's controls, left to right as they are drawn."""
        return (
            self.donate_button,
            self.ui_licence_button,
            self.model_licence_button,
        )
