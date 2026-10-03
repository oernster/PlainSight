"""The reading surface's half of what a document may reach.

The rule is the domain's, in ``document_reach``; this applies it to Qt at the
places Qt acts on an address a document carries.

Two places, because one was measured not to be enough. Every file Qt reads for
a document passes through the pane's loader, which is the gate. But refusing
there with nothing or with empty bytes was measured still drawing a picture
from a network path: Qt reads the picture again by its own name once the
loader's answer will not decode. So the refusal is a real picture; every
picture in a built document is first renamed to the local file the rule
resolves it to (or to no name at all); a refused name then never reaches Qt.
"""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QUrl
from PySide6.QtGui import QImage, QTextCursor, QTextDocument, QTextImageFormat

from ..domain.document_reach import LinkAction, is_inline, link_action, resource_path

# Qt's own picture for one it could not load, so a refused picture looks
# exactly like a missing one rather than leaving a hole.
MISSING_PICTURE = ":/qt-project.org/styles/commonstyle/images/file-16.png"
# Only if Qt's own picture were absent: the smallest picture there is, empty.
STAND_IN_SIDE_PX = 1
TRANSPARENT = 0
NO_NAME = ""
PICTURE_TAG = "<img"

Loader = Callable[[int, QUrl], object]


def refusal() -> QImage:
    """What a refused file is answered with.

    A picture that is never a null one: Qt reads a file again by its own name when
    the answer it is given will not decode, which is the read being refused.
    """
    picture = QImage(MISSING_PICTURE)
    if picture.isNull():
        picture = QImage(
            STAND_IN_SIDE_PX, STAND_IN_SIDE_PX, QImage.Format.Format_ARGB32
        )
        picture.fill(TRANSPARENT)
    return picture


def load_confined(
    kind: int, name: QUrl, document_path: str | None, load: Loader
) -> object:
    """Read what ``name`` names if the rule allows it, else answer the refusal.

    Inline bytes are left to Qt, which decodes them itself and names no file in
    doing so. Anything else is read from the local path the rule resolves it
    to, never from the address as written.
    """
    source = name.toString()
    if is_inline(source):
        return None
    path = resource_path(source, document_path)
    if path is None:
        return refusal()
    loaded = load(kind, QUrl.fromLocalFile(path))
    return refusal() if loaded is None else loaded


def confine_pictures(document: QTextDocument, document_path: str | None) -> None:
    """Rename each picture to the local file it resolves to; else to nothing.

    Collected first and renamed after, since changing a format while walking
    the fragments can merge them under the walk.
    """
    pictures: list[tuple[int, int, QTextImageFormat]] = []
    block = document.begin()
    while block.isValid():
        fragments = block.begin()
        while not fragments.atEnd():
            fragment = fragments.fragment()
            form = fragment.charFormat()
            if form.isImageFormat():
                pictures.append(
                    (fragment.position(), fragment.length(), form.toImageFormat())
                )
            fragments += 1
        block = block.next()
    cursor = QTextCursor(document)
    for position, length, picture in pictures:
        picture.setName(_confined_name(picture.name(), document_path))
        cursor.setPosition(position)
        cursor.setPosition(position + length, QTextCursor.MoveMode.KeepAnchor)
        cursor.setCharFormat(picture)


def holds_pictures(html: str) -> bool:
    """Whether the markup could hold a picture at all, so most pages skip the walk."""
    return PICTURE_TAG in html.lower()


def _confined_name(name: str, document_path: str | None) -> str:
    """The name a picture may keep: its own when inline, a local file, else none."""
    if is_inline(name):
        return name
    path = resource_path(name, document_path)
    return NO_NAME if path is None else QUrl.fromLocalFile(path).toString()


def follow_link(
    address: QUrl,
    scroll_to: Callable[[str], object],
    follow: Callable[[str], object] | None,
) -> None:
    """A web page or a mail goes to ``follow``; a place in the page is scrolled to.

    Anything else does nothing; the pane is never asked to show the
    address, so it never leaves the document the reader chose.
    """
    action = link_action(address.toString())
    if action is LinkAction.IN_PAGE:
        scroll_to(address.fragment())
    elif action is LinkAction.FOLLOW and follow is not None:
        follow(address.toString())
