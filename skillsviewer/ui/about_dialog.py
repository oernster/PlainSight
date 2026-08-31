"""Help and About: who made it, what it is built on and what it is for."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QLabel, QTextBrowser, QVBoxLayout, QWidget

from .. import version
from ..application.ports import AssetLocator
from .auto_scroller import AutoScroller
from .theme import Palette, document_style
from .widgets import FirstStopDialog, close_row

APPLICATION_ICON = "application-icon.png"
ICON_PX = 96
DIALOG_MIN_WIDTH_PX = 560
BODY_MIN_HEIGHT_PX = 320

CREDITS = (
    "<li><b>PySide6</b> (Qt for Python) - LGPL-3.0 (the user interface).</li>"
    "<li><b>Python</b> - PSF licence (the language and its standard library).</li>"
    "<li><b>markdown</b> - BSD (rendering each skill for reading).</li>"
    "<li><b>Pillow</b> - HPND (deriving the icons at build time).</li>"
    "<li><b>pytest</b>, <b>black</b>, <b>flake8</b>, <b>ruff</b> - MIT "
    "(the gates).</li>"
)

ANTHROPIC_NOTE = (
    "<p>Skills Viewer is designed for Claude AI by Anthropic and for no other "
    "AI. It is not affiliated with Anthropic and is not endorsed by them; "
    "Claude and Anthropic are their owners' marks.</p>"
)

LICENCE_NOTE = (
    "<p><b>Licence:</b> the user interface under LGPL-3.0 and everything "
    "beneath it under GPL-3.0. Both are on the buttons in the bottom tray.</p>"
)


class AboutDialog(FirstStopDialog):
    """The application's own account of itself."""

    def __init__(
        self,
        palette: Palette,
        assets: AssetLocator,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"About {version.APP_NAME}")
        self.setMinimumWidth(DIALOG_MIN_WIDTH_PX)

        layout = QVBoxLayout(self)
        badge = _badge(self, assets)
        if badge is not None:
            layout.addWidget(badge)

        self.body = QTextBrowser(self)
        self.body.setObjectName("SkillView")
        self.body.setOpenExternalLinks(True)
        self.body.setMinimumHeight(BODY_MIN_HEIGHT_PX)
        self.body.document().setDefaultStyleSheet(document_style(palette))
        self.body.setHtml(_html())
        self.scroller = AutoScroller(self.body)

        layout.addWidget(self.body)
        layout.addLayout(close_row(self))


def _badge(parent: QWidget, assets: AssetLocator) -> QLabel | None:
    """The application icon, centred above the text."""
    artwork = assets.find(APPLICATION_ICON)
    if artwork is None:
        return None
    label = QLabel(parent)
    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    label.setPixmap(
        QPixmap(artwork).scaled(
            ICON_PX,
            ICON_PX,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
    )
    return label


def _html() -> str:
    """One template, in the order the house About dialogs read."""
    return (
        f"<h2>{version.APP_NAME}</h2>"
        f"<p><b>{version.APP_TAGLINE}</b></p>"
        f"<p><b>Version:</b> {version.__version__}</p>"
        f"<p><b>Author:</b> {version.APP_AUTHOR}</p>"
        f"<p>{version.APP_COPYRIGHT}</p>"
        f"{ANTHROPIC_NOTE}"
        f"{LICENCE_NOTE}"
        "<hr>"
        "<h3>Credit where credit is due</h3>"
        f"<ul>{CREDITS}</ul>"
        "<p>Built on the Python and Qt ecosystems, with thanks to their "
        "communities.</p>"
    )
