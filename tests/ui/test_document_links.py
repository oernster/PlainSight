"""What a click on a link inside a document does.

A document is somebody else's text, so a link in it is somebody else's choice of
what happens next. Only a web page or a mail is handed on; every other scheme
does nothing at all and the pane never leaves the document the reader chose.

Nothing is launched by these tests, whatever the code under test does: every
scheme clicked has a capturing handler registered with the desktop before the
first click and removed after the last.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from PySide6.QtCore import QObject, QPoint, Qt, QUrl, Slot
from PySide6.QtGui import QDesktopServices
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from plainsight.domain.document import Document, DocumentBody, DocumentKind
from plainsight.infrastructure.renderer import DocumentHtmlRenderer
from plainsight.ui.document_view import DocumentView
from plainsight.ui.main_window import NO_LINK_MESSAGE, MainWindow
from plainsight.ui.theme import DARK

VIEW_WIDTH_PX = 700
VIEW_HEIGHT_PX = 500
LINK_TEXT = "CLICKME"
INSIDE_THE_WORD = 2
SETTLE_ROUNDS = 5
FILLER_PARAGRAPHS = 200

FOLLOWED = (
    "https://example.invalid/page",
    "http://example.invalid/page",
    "mailto:someone@example.invalid",
)
REFUSED = (
    "search-ms:query=x&crumb=location:\\\\127.0.0.1\\c$",
    "ms-msdt:/id PCWDiagnostic",
    "ms-settings:privacy",
    "smb://127.0.0.1/c$/",
    "javascript:alert(1)",
)
CAPTURED_SCHEMES = (
    "https",
    "http",
    "mailto",
    "search-ms",
    "ms-msdt",
    "ms-settings",
    "smb",
    "javascript",
    "file",
)


class DesktopCatcher(QObject):
    """Stands in for every desktop handler, so a click launches nothing."""

    def __init__(self) -> None:
        super().__init__()
        self.handed: list[str] = []

    @Slot(QUrl)
    def take(self, url: QUrl) -> None:
        self.handed.append(url.toString())


@pytest.fixture
def desktop(application: QApplication) -> Iterator[DesktopCatcher]:
    catcher = DesktopCatcher()
    for scheme in CAPTURED_SCHEMES:
        QDesktopServices.setUrlHandler(scheme, catcher, "take")
    yield catcher
    for scheme in CAPTURED_SCHEMES:
        QDesktopServices.unsetUrlHandler(scheme)


def a_view(
    body: str, followed: list[str], path: str = "/documents/p.html"
) -> DocumentView:
    """A view showing one HTML document, with its links recorded."""
    view = DocumentView(DocumentHtmlRenderer(), DARK, follow=followed.append)
    show(view, body, path)
    return view


def show(view: DocumentView, body: str, path: str = "/documents/p.html") -> None:
    """Put one HTML document in the view, laid out and settled."""
    view.show_document(
        Document(
            name=Path(path).name,
            path=path,
            kind=DocumentKind.HTML,
            fingerprint=f"{len(body)}:1",
        ),
        lambda: DocumentBody(text=body),
    )
    view.resize(VIEW_WIDTH_PX, VIEW_HEIGHT_PX)
    view.show()
    for _ in range(SETTLE_ROUNDS):
        QApplication.processEvents()


def click_the_link(view: DocumentView) -> None:
    """Click the middle of the link's text, as a reader would."""
    cursor = view.document().find(LINK_TEXT)
    cursor.setPosition(cursor.selectionStart() + INSIDE_THE_WORD)
    centre = view.cursorRect(cursor).center()
    QTest.mouseClick(
        view.viewport(),
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
        QPoint(centre.x(), centre.y()),
    )
    for _ in range(SETTLE_ROUNDS):
        QApplication.processEvents()


def linking_to(href: str) -> str:
    return f'<p><a href="{href}">{LINK_TEXT}</a></p><p>The rest of the page.</p>'


@pytest.mark.parametrize("href", REFUSED)
def test_a_link_of_any_other_scheme_does_nothing(
    desktop: DesktopCatcher, href: str
) -> None:
    followed: list[str] = []
    view = a_view(linking_to(href), followed)

    click_the_link(view)

    assert desktop.handed == []
    assert followed == []
    assert "The rest of the page." in view.toPlainText()


def test_a_file_link_neither_opens_nor_replaces_the_page(
    desktop: DesktopCatcher, tmp_path: Path
) -> None:
    """Measured before the fix: the pane showed the linked file instead."""
    linked = tmp_path / "linked.html"
    linked.write_text("<p>LINKED FILE CONTENT</p>", encoding="utf-8")
    followed: list[str] = []
    view = a_view(linking_to(linked.as_uri()), followed)

    click_the_link(view)

    assert "LINKED FILE CONTENT" not in view.toPlainText()
    assert "The rest of the page." in view.toPlainText()
    assert view.source().isEmpty()
    assert desktop.handed == []
    assert followed == []


@pytest.mark.parametrize("href", FOLLOWED)
def test_a_web_or_mail_link_is_handed_on_and_the_page_stays(
    desktop: DesktopCatcher, href: str
) -> None:
    followed: list[str] = []
    view = a_view(linking_to(href), followed)

    click_the_link(view)

    assert followed == [href]
    # Handed to the application's own opener, never straight to the desktop.
    assert desktop.handed == []
    assert "The rest of the page." in view.toPlainText()


def test_a_link_within_the_page_scrolls_to_its_anchor(desktop: DesktopCatcher) -> None:
    followed: list[str] = []
    filler = "".join(f"<p>Paragraph {n}.</p>" for n in range(FILLER_PARAGRAPHS))
    view = a_view(
        linking_to("#far") + filler + '<p><a name="far"></a>Far down.</p>', followed
    )
    view.scroller.suspend()

    click_the_link(view)

    assert view.verticalScrollBar().value() > 0
    assert followed == []
    assert desktop.handed == []


def test_a_view_given_nowhere_to_send_links_sends_none(
    desktop: DesktopCatcher,
) -> None:
    view = DocumentView(DocumentHtmlRenderer(), DARK)
    show(view, linking_to(FOLLOWED[0]))

    click_the_link(view)

    assert desktop.handed == []
    assert "The rest of the page." in view.toPlainText()


def test_the_window_hands_a_followed_link_to_the_opener(
    window: MainWindow, opener, desktop: DesktopCatcher
) -> None:
    show(window.document_view, linking_to(FOLLOWED[0]))

    click_the_link(window.document_view)

    assert opener.opened == [FOLLOWED[0]]
    assert desktop.handed == []


def test_a_desktop_that_declines_a_link_is_reported(
    window: MainWindow, opener, desktop: DesktopCatcher
) -> None:
    opener.accepts = False
    show(window.document_view, linking_to(FOLLOWED[0]))

    click_the_link(window.document_view)

    assert window.statusBar().currentMessage() == NO_LINK_MESSAGE
