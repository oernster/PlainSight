"""The Guide: what the screens cannot say for themselves.

Two jobs, in this order. It NAMES the furniture, each entry carrying the real
icon the tray actually draws, so a picture that replaced a word can be
identified by somebody who has just met it. Then it says the one thing no
screen can state on its own: what each kind of document BECOMES on the way to
the pane, which is the whole of what this application does and is invisible
while it is working.

It is deliberately short. Anything a control says for itself is left to the
control: every button here carries a tooltip, so this screen names them rather
than explaining them. A help screen nobody finishes explains nothing.

Every entry carries the REAL icon, pulled through the same asset lookup the
tray uses. Never a description in words; never a similar-looking emoji
standing in for a picture. An icon guide showing something other than the icon
is worse than no guide.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QVBoxLayout, QWidget

from .. import version
from ..application.ports import AssetLocator
from .bottom_tray import DONATE_ICON, MODEL_LICENCE_ICON, UI_LICENCE_ICON
from .reading_pane import ReadingPane
from .theme import Palette, document_style
from .top_tray import (
    CHOOSE_EDITOR_ICON,
    DARK_MODE_ICON,
    FOLDER_ICON,
    HELP_ICON,
    LAUNCH_EDITOR_ICON,
    LIGHT_MODE_ICON,
    OPEN_FILE_ICON,
)
from .widgets import FirstStopDialog, close_row

GUIDE_TITLE = f"How {version.APP_NAME} works"
DIALOG_MIN_WIDTH_PX = 640
BODY_MIN_HEIGHT_PX = 520

# The size an icon is drawn at inside the text. Bigger than the words it sits
# among, on purpose: this screen is read to IDENTIFY a picture rather than to
# skim a sentence; the artwork carries detail that closes up when it is
# set at the height of a line.
INLINE_ICON_PX = 30

MEDIUM_FONT_ICON = "medium-font.png"
DOT = "&nbsp;&middot;&nbsp;"


class GuideDialog(FirstStopDialog):
    """Names every picture in the trays, then says what a document becomes."""

    def __init__(
        self,
        palette: Palette,
        assets: AssetLocator,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(GUIDE_TITLE)
        self.setMinimumWidth(DIALOG_MIN_WIDTH_PX)

        layout = QVBoxLayout(self)
        self.body = ReadingPane(self)
        self.body.setOpenExternalLinks(True)
        self.body.setMinimumHeight(BODY_MIN_HEIGHT_PX)
        self.body.document().setDefaultStyleSheet(document_style(palette))
        self.body.setHtml(guide_html(assets))

        layout.addWidget(self.body)
        layout.addLayout(close_row(self))


def _img(assets: AssetLocator, name: str) -> str:
    """One tray icon as an inline picture; nothing at all where it is missing.

    Nothing rather than a placeholder: the line still reads without its
    picture; a missing asset must never be what stops the guide opening.

    Centred on the line rather than left on its baseline. At this size a
    picture sitting on the baseline hangs below the words it leads, which
    reads as the row having slipped rather than as an icon in a sentence.
    """
    found = assets.find(name)
    if found is None:
        return ""
    return (
        f'<img src="{Path(found).resolve().as_uri()}" '
        f'width="{INLINE_ICON_PX}" height="{INLINE_ICON_PX}" '
        'style="vertical-align: middle"> '
    )


def guide_html(assets: AssetLocator) -> str:
    """The guide, with every icon resolved at the moment it is opened."""
    return "".join(
        (
            f"<h2>{GUIDE_TITLE}</h2>",
            _top_tray(assets),
            _foot(assets),
            _choosing(),
            _kinds(),
            _reading(),
            _keyboard(),
        )
    )


def _top_tray(assets: AssetLocator) -> str:
    """The row above the body, named picture by picture, left to right."""
    return (
        "<h3>The tray along the top</h3>"
        f"<p>{_img(assets, FOLDER_ICON)}choose the folder your documents live in"
        f"{DOT}{_img(assets, OPEN_FILE_ICON)}open one document on its own</p>"
        f"<p>{_img(assets, CHOOSE_EDITOR_ICON)}choose the editor"
        f"{DOT}{_img(assets, LAUNCH_EDITOR_ICON)}open the selected document in it</p>"
        f"<p>{_img(assets, MEDIUM_FONT_ICON)}step the text size"
        f"{DOT}{_img(assets, LIGHT_MODE_ICON)}/{_img(assets, DARK_MODE_ICON)}"
        f"light or dark{DOT}{_img(assets, HELP_ICON)}About, this guide and the "
        "update check</p>"
        "<p>Rest the pointer on any of them and it says its name. Two of them "
        "show what a press would move TO rather than where you are now, which "
        "is why the sun appears while you are sitting in the dark and the size "
        "button wears the size it would give you next.</p>"
        "<p>The editor button stays dim, wearing a red ring, until a document "
        "is selected. There is nothing for it to open before that.</p>"
    )


def _foot(assets: AssetLocator) -> str:
    """The strip under the body, which sits in no other list."""
    return (
        "<hr><h3>The strip along the foot</h3>"
        f"<p>{_img(assets, DONATE_ICON)}buy the author a drink"
        f"{DOT}{_img(assets, UI_LICENCE_ICON)}the user interface licence"
        f"{DOT}{_img(assets, MODEL_LICENCE_ICON)}the model licence</p>"
        "<p>The drink hands an address to your browser and opens nothing "
        "here; PlainSight itself sends nothing. Nothing in the application is "
        "held back behind it.</p>"
    )


def _choosing() -> str:
    """Why the window starts empty, which looks like a fault and is not."""
    return (
        "<hr><h3>Nothing is read until you choose</h3>"
        "<p>There is no default folder and no first-run scan, so a fresh "
        "install has looked at nothing on the machine. The chooser opens on "
        "your home directory, the one starting place no operating system "
        "asks you to approve. Point it at a Claude skills folder and the "
        "plugins tree "
        "beside it comes too, as a second root; point it anywhere else and "
        "that one folder is read, with nothing beside it touched.</p>"
        "<p>Nothing is selected either. The pane stays empty and says so, "
        "rather than choosing something for you to look at.</p>"
        "<p>The tree is the folders as they are on disk, to whatever depth "
        "they go. Each folder carries a count, so a shut branch tells you "
        "whether it is worth opening; a branch leading to no document at "
        "all is not listed. The ones you leave open are remembered.</p>"
    )


def _kinds() -> str:
    """What a document becomes, which is the whole job and is invisible."""
    return (
        "<hr><h3>What each kind becomes</h3>"
        "<p>A document is shown as something to read rather than as the "
        "characters in the file. What that means differs by kind; this is "
        "the one thing no screen can tell you while it is happening.</p>"
        "<p><b>Markdown</b> is rendered, with whatever it declares in its "
        "frontmatter laid out above the body. It is the only kind that "
        "declares fields.</p>"
        "<p><b>Plain text</b> is shown exactly as it was typed. Its line "
        "breaks are the author's own layout, so three hyphens stay three "
        "hyphens rather than becoming a rule.</p>"
        "<p><b>HTML</b> is shown as the page it already is. Its scripts are "
        "dropped rather than run and nothing is fetched from the network, so "
        "a page somebody sent you cannot act on your machine.</p>"
        "<p><b>Word</b> is turned into HTML as it is read: headings, "
        "paragraphs, lists, tables and the emphasis inside them. A table Word "
        "was using to arrange the page, rather than to tabulate anything, "
        "gives up its contents as the paragraphs they are.</p>"
        "<p><b>PDF</b> is read back into the document its page was laid out "
        "to be. A PDF holds no headings, no paragraphs and no lists; it holds "
        "glyphs, each with a place, a size and a face. So the sizes and the "
        "faces are read the way your eye reads them: larger than the body is "
        "a heading, bold is emphasis, a bullet opens an item. That is a "
        "reading of the page rather than anything the file says, so a form's "
        "grid becomes reading order. A scan holds no text to take and says "
        "so; one that is locked says that on its row before you open it.</p>"
    )


def _reading() -> str:
    """The two habits of the pane that surprise a reader who has not met them."""
    return (
        "<hr><h3>Reading one</h3>"
        "<p>The page reads itself gently down and hands control straight back "
        "the moment you scroll. The text is held to a readable column, so a "
        "wide window buys margins rather than longer lines.</p>"
        "<p>Changing the size or the appearance keeps your place: you stay on "
        "the words you were reading rather than being thrown to the top.</p>"
        "<p>Nothing you do here changes a document. It is never written to, "
        "which is enforced by a test rather than left to good intentions; "
        "editing is handed to the editor you chose. The folder is read again "
        "whenever the window comes back to the front, so a document edited "
        "elsewhere is current when you return to it.</p>"
    )


def _keyboard() -> str:
    """The ring, stated once, because a ring is not discoverable by looking."""
    return (
        "<hr><h3>Keyboard</h3>"
        "<p>Tab or Right goes forward, Shift+Tab or Left goes back, wrapping "
        "at both ends. Enter does what Space does. In the tree, Up and Down "
        "walk the rows and Enter or Space works a folder's arrow.</p>"
        "<p>A region of text is a stop only while it has somewhere to scroll; "
        "Home and End reach its ends. Nothing is highlighted on the main "
        "window until your first keypress, whereas a dialog you open starts "
        "on its own first control, because you opened it to do one thing.</p>"
    )
