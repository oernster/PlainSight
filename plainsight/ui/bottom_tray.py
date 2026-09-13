"""The bottom tray: donate and the two licences at the left, the filter right."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QHBoxLayout, QPushButton, QWidget

from ..application.ports import AssetLocator
from .widgets import icon_button

DONATE_ICON = "donate.png"
UI_LICENCE_ICON = "ui-licence.png"
MODEL_LICENCE_ICON = "model-licence.png"
TREE_FILTER_ICON = "tree-filter.png"
NEGATIVE_ICON = "negative-mark.png"

DONATE_TOOLTIP = "Buy the author a drink (opens your browser)"
UI_LICENCE_TOOLTIP = "The user interface licence (LGPL-3.0)"
MODEL_LICENCE_TOOLTIP = "The model licence (GPL-3.0)"
HIDE_TOOLTIP = "Hide venv, node_modules and empty documents"
SHOW_TOOLTIP = "Show venv, node_modules and empty documents"

TRAY_SCALE = 1.5
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
        on_filter: Callable[[], None],
    ) -> None:
        super().__init__(parent)
        self._assets = assets
        # A container is never a stop, so it is said rather than assumed.
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.donate_button = icon_button(
            self, assets.find(DONATE_ICON), DONATE_TOOLTIP, on_donate, TRAY_SCALE
        )
        self.ui_licence_button = icon_button(
            self,
            assets.find(UI_LICENCE_ICON),
            UI_LICENCE_TOOLTIP,
            on_ui_licence,
            TRAY_SCALE,
        )
        self.model_licence_button = icon_button(
            self,
            assets.find(MODEL_LICENCE_ICON),
            MODEL_LICENCE_TOOLTIP,
            on_model_licence,
            TRAY_SCALE,
        )
        # It wears what a press would move TO, as the appearance toggle does.
        # The filter starts on, so the button starts offering to show again.
        self.filter_button = icon_button(
            self, None, SHOW_TOOLTIP, on_filter, TRAY_SCALE
        )
        self.face_filter(True)

        row = QHBoxLayout(self)
        row.setContentsMargins(
            TRAY_MARGIN_PX, TRAY_MARGIN_PX, TRAY_MARGIN_PX, TRAY_MARGIN_PX
        )
        row.setSpacing(TRAY_SPACING_PX)
        row.addWidget(self.donate_button)
        row.addWidget(self.ui_licence_button)
        row.addWidget(self.model_licence_button)
        row.addStretch()
        row.addWidget(self.filter_button)

    def ring_stops(self) -> tuple[QPushButton, ...]:
        """This tray's controls, left to right as they are drawn."""
        return (
            self.donate_button,
            self.ui_licence_button,
            self.model_licence_button,
            self.filter_button,
        )

    def face_filter(self, filter_on: bool) -> None:
        """Wear what a press would do: show again while on; hide while off.

        While the filter is on, the picture wears the cross, since a press
        takes the filter away. While it is off, the picture stands alone.
        """
        picture = filter_picture(self._assets, filter_on)
        if picture is not None:
            self.filter_button.setIcon(QIcon(picture))
        tooltip = SHOW_TOOLTIP if filter_on else HIDE_TOOLTIP
        self.filter_button.setToolTip(tooltip)
        self.filter_button.setAccessibleName(tooltip)


def filter_picture(assets: AssetLocator, filter_on: bool) -> QPixmap | None:
    """The filter picture, under the cross while the filter is on.

    None when the picture was not bundled; the button keeps its words then.
    A missing cross costs only the cross.
    """
    found = assets.find(TREE_FILTER_ICON)
    if found is None:
        return None
    picture = QPixmap(found)
    cross = assets.find(NEGATIVE_ICON) if filter_on else None
    return picture if cross is None else overlaid(picture, QPixmap(cross))


def overlaid(picture: QPixmap, overlay: QPixmap) -> QPixmap:
    """``overlay`` drawn over ``picture``, centred and fitted inside it.

    Composed at runtime rather than stored as a third picture, so the filter
    and the cross each keep one source and the pair cannot drift apart. The
    overlay is only ever scaled down to fit, never up. What is clear in both
    stays clear, so the button keeps its transparent ground.
    """
    fitted = overlay
    if overlay.width() > picture.width() or overlay.height() > picture.height():
        fitted = overlay.scaled(
            picture.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
    laid = QPixmap(picture.size())
    laid.fill(Qt.GlobalColor.transparent)
    target = fitted.rect()
    target.moveCenter(laid.rect().center())
    painter = QPainter(laid)
    painter.drawPixmap(laid.rect(), picture)
    painter.drawPixmap(target, fitted)
    painter.end()
    return laid
