"""How the folder arrow is drawn: one arrow per folder, in the palette worn.

Separated from the tree's behaviour because these read pixels rather than
state: they render the widget and count ink, which is the only way to tell a
drawn arrow from the toolkit's own.
"""

from __future__ import annotations

from PySide6.QtGui import QColor, QPixmap
from PySide6.QtWidgets import QApplication

from plainsight.domain.document import Document, DocumentKind
from plainsight.domain.library import Folder, Library
from plainsight.domain.settings import FontSize
from plainsight.ui.library_tree import ARROW_PX, FIRST_COLUMN, LibraryTree, arrow_icon
from plainsight.ui.theme import DARK, LIGHT, stylesheet

MINIMUM_TARGET_PX = 20
NO_INK = 0


def a_document(name: str, folder: str) -> Document:
    return Document(
        name=name,
        path=f"{folder}/{name}",
        kind=DocumentKind.MARKDOWN,
        body="Body.",
    )


SKILLS = Folder.of(
    "skills",
    "/skills",
    folders=[
        Folder.of(
            "prose",
            "/skills/prose",
            documents=[a_document("SKILL.md", "/skills/prose")],
        )
    ],
    documents=[a_document("loose.md", "/skills")],
)
PLUGINS = Folder.of(
    "plugins", "/plugins", documents=[a_document("SKILL.md", "/plugins")]
)
BOTH = Library((SKILLS, PLUGINS))


def a_tree(library: Library, opened: tuple[str, ...] = ()) -> LibraryTree:
    tree = LibraryTree(DARK, opened)
    tree.show_library(library)
    tree.show()
    QApplication.processEvents()
    return tree


def test_the_two_arrows_are_drawn_and_differ(application) -> None:
    """Drawn rather than styled, so the shape can be read back here."""
    open_arrow = arrow_icon(DARK.muted, True).pixmap(ARROW_PX, ARROW_PX).toImage()
    shut_arrow = arrow_icon(DARK.muted, False).pixmap(ARROW_PX, ARROW_PX).toImage()

    inked = [
        sum(
            1
            for y in range(ARROW_PX)
            for x in range(ARROW_PX)
            if image.pixelColor(x, y).alpha() > 0
        )
        for image in (open_arrow, shut_arrow)
    ]

    assert all(count > 0 for count in inked)
    assert open_arrow != shut_arrow


def test_the_arrows_are_redrawn_in_the_palette_being_worn(application) -> None:
    tree = a_tree(BOTH)
    before = (
        tree.topLevelItem(0).icon(FIRST_COLUMN).pixmap(ARROW_PX, ARROW_PX).toImage()
    )

    tree.wear(LIGHT)
    after = tree.topLevelItem(0).icon(FIRST_COLUMN).pixmap(ARROW_PX, ARROW_PX).toImage()

    assert before != after


def _branch_strip_ink(tree: LibraryTree, item) -> int:
    """Pixels differing from the panel behind a row, left of its own indent.

    Nothing of ours is drawn there: the row's own arrow is the item icon, which
    begins after the indent. Ink in that strip can only be the toolkit's own
    branch indicator.
    """
    pixmap = QPixmap(tree.size())
    tree.render(pixmap)
    image = pixmap.toImage()
    rect = tree.visualItemRect(item)
    background = QColor(DARK.panel)
    return sum(
        1
        for y in range(max(rect.top(), 0), min(rect.bottom(), image.height() - 1))
        for x in range(min(tree.indentation(), image.width()))
        if image.pixelColor(x, y) != background
    )


def test_a_nested_folder_draws_one_arrow_rather_than_two(application) -> None:
    """The toolkit's own branch indicator is suppressed, ours is not.

    `setRootIsDecorated(False)` hides the indicator on top level rows alone, so
    nesting reintroduced it one level down and every folder beneath a root
    carried a small arrow beside the drawn one. Measured before the stylesheet
    rule: 20 inked pixels in that strip on a nested row against 2 on a top
    level one.
    """
    application.setStyleSheet(stylesheet(DARK, FontSize.MEDIUM))
    tree = a_tree(BOTH)
    tree.topLevelItem(0).setExpanded(True)
    QApplication.processEvents()
    nested = tree.topLevelItem(0).child(0)

    assert _branch_strip_ink(tree, nested) == NO_INK
    assert not nested.icon(FIRST_COLUMN).isNull()


def test_the_arrow_is_big_enough_to_read_as_a_control(application) -> None:
    """It is something you click, so it needs a target rather than a glyph.

    The figure is a stated minimum rather than a measurement: this harness has
    no real fonts, so its text metrics cannot be used to justify one. At the
    twelve pixels it began at, the arrow read as a speck.
    """
    tree = a_tree(BOTH)

    assert ARROW_PX >= MINIMUM_TARGET_PX
    assert tree.iconSize().width() == ARROW_PX
