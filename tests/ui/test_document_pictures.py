"""Where a document's pictures may come from.

A picture is read from this computer only: from the document's own folder when
it is named relatively, from a local path when it is named absolutely. Anything
naming a host is refused before it is read, which is what keeps opening a
received document from reaching a network share.

Network paths are only ever the loopback administrative share of this machine;
no other host is named in a read.
"""

from __future__ import annotations

import base64
import os
import sys
from pathlib import Path

import pytest
from PySide6.QtCore import QUrl
from PySide6.QtGui import QColor, QImage, QTextDocument
from PySide6.QtWidgets import QApplication

from plainsight.domain.document import Document, DocumentBody, DocumentKind
from plainsight.domain.document_reach import resource_path
from plainsight.infrastructure.renderer import DocumentHtmlRenderer
from plainsight.ui.document_view import DocumentView
from plainsight.ui.theme import DARK

VIEW_WIDTH_PX = 600
VIEW_HEIGHT_PX = 400
PICTURE_PX = 24
SAMPLE_STEP_PX = 4
SETTLE_ROUNDS = 10
GREEN = QColor(0, 255, 0)
LOOPBACK = "127.0.0.1"


def a_picture(path: Path) -> Path:
    """A picture of a colour nothing else on the page is drawn in."""
    path.parent.mkdir(parents=True, exist_ok=True)
    image = QImage(PICTURE_PX, PICTURE_PX, QImage.Format.Format_ARGB32)
    image.fill(GREEN)
    assert image.save(str(path))
    return path


def showing(path: Path, kind: DocumentKind, source: str) -> DocumentView:
    """A view reading one document at ``path`` that embeds ``source``."""
    body = (
        f'<p>Text.</p><img src="{source}">'
        if kind is DocumentKind.HTML
        else f"Text.\n\n![x]({source})\n"
    )
    return showing_body(path, kind, body)


def showing_body(path: Path, kind: DocumentKind, body: str) -> DocumentView:
    view = DocumentView(DocumentHtmlRenderer(), DARK)
    view.show_document(
        Document(
            name=path.name, path=str(path), kind=kind, fingerprint=f"{len(body)}:1"
        ),
        lambda: DocumentBody(text=body),
    )
    view.resize(VIEW_WIDTH_PX, VIEW_HEIGHT_PX)
    view.show()
    for _ in range(SETTLE_ROUNDS):
        QApplication.processEvents()
    return view


def draws_the_picture(view: DocumentView) -> bool:
    """Whether the green picture is on screen, read off the pane's own pixels."""
    image = view.viewport().grab().toImage()
    return any(
        image.pixelColor(x, y) == GREEN
        for x in range(0, image.width(), SAMPLE_STEP_PX)
        for y in range(0, image.height(), SAMPLE_STEP_PX)
    )


def loopback_forms(picture: Path) -> dict[str, str]:
    """The picture by way of this machine's own administrative share."""
    drive, rest = os.path.splitdrive(str(picture))
    tail = drive.rstrip(":").lower() + "$" + rest
    forward = tail.replace("\\", "/")
    return {
        "file_url_with_host": f"file://{LOOPBACK}/{forward}",
        "protocol_relative": f"//{LOOPBACK}/{forward}",
        "backslash_unc": f"\\\\{LOOPBACK}\\{tail}",
    }


def loopback_share_is_readable(picture: Path) -> bool:
    """Only a share that really serves the file makes a refusal mean anything."""
    if sys.platform != "win32":
        return False
    return Path(loopback_forms(picture)["backslash_unc"]).exists()


KINDS = (DocumentKind.HTML, DocumentKind.MARKDOWN)
FORMS = ("file_url_with_host", "protocol_relative", "backslash_unc")


@pytest.mark.parametrize("kind", KINDS)
def test_a_picture_by_a_local_absolute_path_is_drawn(
    tmp_path: Path, kind: DocumentKind
) -> None:
    """The control: the same picture the refusals below are about does draw."""
    picture = a_picture(tmp_path / "pictures" / "pic.png")

    view = showing(tmp_path / "doc" / "page.md", kind, picture.as_posix())

    assert draws_the_picture(view)


@pytest.mark.parametrize("form", FORMS)
@pytest.mark.parametrize("kind", KINDS)
def test_a_picture_on_a_network_path_is_never_read(
    tmp_path: Path, kind: DocumentKind, form: str
) -> None:
    picture = a_picture(tmp_path / "pictures" / "pic.png")
    if not loopback_share_is_readable(picture):
        pytest.skip("this machine serves no loopback administrative share")

    view = showing(tmp_path / "doc" / "page.md", kind, loopback_forms(picture)[form])

    assert not draws_the_picture(view)


def test_a_background_on_a_network_path_is_never_read(tmp_path: Path) -> None:
    picture = a_picture(tmp_path / "pictures" / "pic.png")
    if not loopback_share_is_readable(picture):
        pytest.skip("this machine serves no loopback administrative share")
    source = loopback_forms(picture)["protocol_relative"]

    view = showing_body(
        tmp_path / "doc" / "page.html",
        DocumentKind.HTML,
        f'<table background="{source}" width="100%" height="200">'
        "<tr><td>T.</td></tr></table>",
    )

    assert not draws_the_picture(view)


@pytest.mark.parametrize("kind", KINDS)
def test_a_picture_beside_the_document_is_drawn(
    tmp_path: Path, kind: DocumentKind, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Named relatively, it is looked for in the document's own folder."""
    a_picture(tmp_path / "doc" / "pic.png")
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)

    view = showing(tmp_path / "doc" / "page.md", kind, "pic.png")

    assert draws_the_picture(view)


def test_a_relative_picture_is_not_looked_for_in_the_working_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "doc").mkdir()
    a_picture(tmp_path / "cwd" / "pic.png")
    monkeypatch.chdir(tmp_path / "cwd")

    view = showing(tmp_path / "doc" / "page.md", DocumentKind.MARKDOWN, "pic.png")

    assert not draws_the_picture(view)


def test_a_relative_picture_may_climb_out_while_it_stays_on_this_computer(
    tmp_path: Path,
) -> None:
    a_picture(tmp_path / "pictures" / "pic.png")

    view = showing(
        tmp_path / "doc" / "page.md", DocumentKind.MARKDOWN, "../pictures/pic.png"
    )

    assert draws_the_picture(view)


def test_an_inline_picture_is_still_drawn(tmp_path: Path) -> None:
    picture = a_picture(tmp_path / "pictures" / "pic.png")
    encoded = base64.b64encode(picture.read_bytes()).decode()

    view = showing(
        tmp_path / "doc" / "page.html",
        DocumentKind.HTML,
        f"data:image/png;base64,{encoded}",
    )

    assert draws_the_picture(view)


@pytest.mark.parametrize(
    "address",
    (
        f"file://{LOOPBACK}/c$/nothing.png",
        f"//{LOOPBACK}/c$/nothing.png",
        f"\\\\{LOOPBACK}\\c$\\nothing.png",
        f"http://{LOOPBACK}:9/nothing.png",
        f"smb://{LOOPBACK}/c$/nothing.png",
    ),
)
def test_the_loader_refuses_an_address_with_a_host(
    tmp_path: Path, address: str
) -> None:
    """Asked directly, the pane's loader gives the refusal, never bytes."""
    view = showing_body(tmp_path / "page.html", DocumentKind.HTML, "<p>T.</p>")

    loaded = view.loadResource(QTextDocument.ResourceType.ImageResource, QUrl(address))

    assert isinstance(loaded, QImage)
    assert loaded.pixelColor(0, 0) != GREEN


def test_no_picture_in_a_shown_document_keeps_a_name_the_rule_refuses(
    tmp_path: Path,
) -> None:
    """Every picture is renamed to the local file it resolves to; else to nothing.

    Qt's own image handling acts on a picture's name directly in places a
    loader never sees, so a refused name must not survive into the document.
    """
    a_picture(tmp_path / "doc" / "pic.png")
    page = tmp_path / "doc" / "page.html"
    view = showing_body(
        page,
        DocumentKind.HTML,
        f'<img src="pic.png"><img src="//{LOOPBACK}/c$/x.png">'
        f'<img src="file://{LOOPBACK}/c$/x.png">',
    )

    names = picture_names(view.document())

    assert len(names) == 3
    for name in names:
        assert name == "" or QUrl(name).isLocalFile()
        assert name == "" or resource_path(name, str(page)) is not None


def picture_names(document: QTextDocument) -> list[str]:
    names: list[str] = []
    block = document.begin()
    while block.isValid():
        fragments = block.begin()
        while not fragments.atEnd():
            form = fragments.fragment().charFormat()
            if form.isImageFormat():
                names.append(form.toImageFormat().name())
            fragments += 1
        block = block.next()
    return names
