"""What the reading surface does with an HTML document.

Every assertion here was measured against a real ``QTextBrowser`` before it was
written down. They are guards on two claims the application makes out loud: it
runs nothing a document carries; it fetches nothing on a document's
behalf. Both are properties of Qt's rich text engine rather than of any code in
this repository, so they are pinned here where a toolkit upgrade would show up.
"""

from __future__ import annotations

import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from PySide6.QtWidgets import QApplication

from plainsight.domain.document import Document, DocumentBody, DocumentKind
from plainsight.infrastructure.renderer import DocumentHtmlRenderer
from plainsight.ui.document_view import DocumentView
from plainsight.ui.theme import DARK

VIEW_WIDTH_PX = 700
VIEW_HEIGHT_PX = 500
NOTHING_REQUESTED = 0
ONE_PIXEL_PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
    "0000000a49444154789c636000000200010005fe02fea735819d0000000049454e"
    "44ae426082"
)


def an_html_view(body: str) -> DocumentView:
    """A view showing one HTML document, laid out and settled."""
    view = DocumentView(DocumentHtmlRenderer(), DARK)
    view.show_document(
        Document(
            name="page.html",
            path="/documents/page.html",
            kind=DocumentKind.HTML,
            fingerprint=f"{len(body)}:1",
        ),
        lambda: DocumentBody(text=body),
    )
    view.resize(VIEW_WIDTH_PX, VIEW_HEIGHT_PX)
    view.document().adjustSize()
    QApplication.processEvents()
    return view


def test_an_html_document_renders_rather_than_showing_its_own_source() -> None:
    view = an_html_view("<h1>Page heading</h1><p>A paragraph.</p>")

    text = view.toPlainText()

    assert "Page heading" in text
    assert "<h1>" not in text


def test_a_whole_page_survives_being_shown_beneath_a_header() -> None:
    """The pane is handed a header and the document as one string.

    A whole page therefore arrives nested inside another document. Qt absorbs
    the outer elements rather than showing them, which is the only reason a
    saved page reads at all.
    """
    view = an_html_view(
        "<!DOCTYPE html>\n<html><head><title>T</title>"
        "<style>p { color: #222222; }</style></head>"
        "<body><p>Body paragraph.</p></body></html>"
    )

    text = view.toPlainText()

    assert "Body paragraph." in text
    assert "DOCTYPE" not in text
    assert "color" not in text


def test_a_script_in_a_document_neither_runs_nor_is_shown() -> None:
    """Qt has no script engine, so a document cannot act on the reader.

    Both halves matter. A script that ran would be the whole security story;
    a script that leaked as text would put its source in the middle of the
    page the reader wanted.
    """
    view = an_html_view(
        "<p>Before.</p>" "<script>document.title = 'RAN';</script>" "<p>After.</p>"
    )

    text = view.toPlainText()

    assert "Before." in text
    assert "After." in text
    assert "document.title" not in text
    assert "RAN" not in text
    assert view.documentTitle() != "RAN"


def test_htmx_attributes_are_inert_and_leave_only_their_text() -> None:
    """htmx needs a script runtime, so its attributes describe nothing here."""
    view = an_html_view(
        '<button hx-get="/clicked" hx-swap="outerHTML">Press me</button>'
        '<div hx-post="/data" hx-trigger="load">Some text</div>'
    )

    text = view.toPlainText()
    stored = view.toHtml()

    assert "Press me" in text
    assert "Some text" in text
    for attribute in ("hx-get", "hx-post", "hx-swap", "hx-trigger"):
        assert attribute not in stored


def test_a_document_embedding_a_remote_picture_fetches_nothing() -> None:
    """The guard on what the application says about the network.

    It claims exactly one network request of its own. A document that could
    make it fetch something would break that claim quietly, so the claim is
    tested against a real server rather than reasoned about: the server is
    asked whether it was ever called.
    """
    received: list[str] = []

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            received.append(self.path)
            self.send_response(200)
            self.send_header("Content-Type", "image/png")
            self.send_header("Content-Length", str(len(ONE_PIXEL_PNG)))
            self.end_headers()
            self.wfile.write(ONE_PIXEL_PNG)

        def log_message(self, *arguments: object) -> None:
            """Silent: a test that printed a server log would read as a failure."""

    server = HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        address = f"http://127.0.0.1:{server.server_port}/picture.png"
        view = an_html_view(f'<p>Text.</p><img src="{address}" alt="remote">')
        for _ in range(50):
            QApplication.processEvents()

        assert "Text." in view.toPlainText()
        assert len(received) == NOTHING_REQUESTED
    finally:
        server.shutdown()
        server.server_close()
        thread.join()
