"""The library tree: its folders, its arrows and what it refuses to choose."""

from __future__ import annotations

from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import QApplication

from plainsight.domain.document import Document, DocumentKind
from plainsight.domain.library import Folder, Library
from plainsight.ui.library_tree import ARROW_PX, FIRST_COLUMN, LibraryTree, arrow_icon
from plainsight.ui.theme import DARK, LIGHT

MINIMUM_TARGET_PX = 20


def a_document(name: str, folder: str) -> Document:
    return Document(
        name=name,
        path=f"{folder}/{name}",
        kind=DocumentKind.MARKDOWN,
        description=f"about {name}",
        body="Body.",
    )


def a_root(name: str, path: str, *documents: str) -> Folder:
    return Folder.of(name, path, documents=[a_document(one, path) for one in documents])


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
PLUGINS = a_root("plugins", "/plugins", "SKILL.md")
BOTH = Library((SKILLS, PLUGINS))
ONE = Library((SKILLS,))


def a_tree(library: Library, opened: tuple[str, ...] = ()) -> LibraryTree:
    tree = LibraryTree(DARK, opened)
    tree.show_library(library)
    tree.show()
    QApplication.processEvents()
    return tree


def press(tree: LibraryTree, key: Qt.Key) -> None:
    QApplication.sendEvent(
        tree, QKeyEvent(QEvent.Type.KeyPress, key, Qt.KeyboardModifier.NoModifier)
    )


def labels(items: list) -> list[str]:
    return [item.text(FIRST_COLUMN) for item in items]


def test_each_root_is_a_row_of_its_own(application) -> None:
    tree = a_tree(BOTH)

    tops = [tree.topLevelItem(row) for row in range(tree.topLevelItemCount())]

    assert labels(tops) == ["skills (2)", "plugins (1)"]


def test_a_folder_row_counts_everything_beneath_it(application) -> None:
    """The count is what tells a reader whether a shut branch is worth opening."""
    tree = a_tree(BOTH)

    assert "skills (2)" in labels(tree.folder_items())
    assert "prose (1)" in labels(tree.folder_items())


def test_the_tree_mirrors_the_folders_on_disk(application) -> None:
    tree = a_tree(BOTH)

    assert labels(tree.document_items()) == ["SKILL.md", "loose.md", "SKILL.md"]


def test_a_document_row_carries_the_file_name(application) -> None:
    """Not the declared name: a reader has to be able to find the file again."""
    tree = a_tree(ONE)

    assert "SKILL.md" in labels(tree.document_items())


def test_an_unreadable_document_says_so_on_its_row(application) -> None:
    broken = Document(
        name="broken.md",
        path="/skills/broken.md",
        kind=DocumentKind.MARKDOWN,
        body="",
        failure="Could not be read.",
    )
    tree = a_tree(Library((Folder.of("skills", "/skills", documents=[broken]),)))

    assert labels(tree.document_items()) == ["broken.md (unreadable)"]


def test_every_folder_opens_shut(application) -> None:
    """A library of hundreds is a wall of rows; it opens as a short list instead."""
    tree = a_tree(BOTH)

    assert [item.isExpanded() for item in tree.folder_items()] == [False, False, False]


def test_a_folder_the_reader_left_open_opens_open(application) -> None:
    tree = a_tree(BOTH, opened=("/plugins",))

    opened = [
        item.text(FIRST_COLUMN) for item in tree.folder_items() if item.isExpanded()
    ]

    assert opened == ["plugins (1)"]


def test_a_folder_is_remembered_by_its_path_rather_than_its_label(
    application,
) -> None:
    """Two folders can share a name; only the path tells them apart."""
    tree = a_tree(BOTH)
    reported: list[tuple] = []
    tree.folders_changed.connect(reported.append)
    folder = tree.topLevelItem(0)

    folder.setExpanded(True)
    folder.setExpanded(False)

    assert reported == [("/skills",), ()]


def test_enter_opens_a_folder_and_shuts_it_again(application) -> None:
    tree = a_tree(BOTH)
    folder = tree.topLevelItem(0)
    tree.setCurrentItem(folder)

    press(tree, Qt.Key.Key_Return)
    opened = folder.isExpanded()
    press(tree, Qt.Key.Key_Return)

    assert opened
    assert not folder.isExpanded()


def test_space_toggles_a_folder_too(application) -> None:
    tree = a_tree(BOTH)
    folder = tree.topLevelItem(0)
    tree.setCurrentItem(folder)

    press(tree, Qt.Key.Key_Space)

    assert folder.isExpanded()


def test_a_key_on_a_document_row_toggles_nothing(application) -> None:
    """Only a folder toggles; a document has nothing to open or close."""
    tree = a_tree(BOTH)
    for item in tree.folder_items():
        item.setExpanded(True)
    tree.setCurrentItem(tree.document_items()[0])
    before = [item.isExpanded() for item in tree.folder_items()]

    press(tree, Qt.Key.Key_Space)

    assert [item.isExpanded() for item in tree.folder_items()] == before


def test_a_folder_the_reader_opened_stays_open_on_a_re_read(application) -> None:
    tree = a_tree(BOTH)
    tree.topLevelItem(0).setExpanded(True)

    tree.show_library(BOTH)

    assert tree.topLevelItem(0).isExpanded()


def test_nothing_is_selected_until_the_reader_selects_something(
    application,
) -> None:
    """The pane reads itself down the page, so a default choice starts reading.

    Qt makes a row current of its own accord when a tree is filled and shown.
    That is harmless here and is asserted rather than wished away: a root is
    always a folder, so the row Qt lands on can never be a document; a folder
    announces nothing.
    """
    tree = a_tree(BOTH)
    announced: list[Document] = []
    tree.document_selected.connect(announced.append)

    assert tree.selected_document() is None
    assert tree.currentItem() not in tree.document_items()
    assert announced == []


def test_a_re_read_still_selects_nothing_when_nothing_was_selected(
    application,
) -> None:
    """The library is re-read on every activation, so this happens constantly."""
    tree = a_tree(BOTH)

    tree.show_library(BOTH)

    assert tree.selected_document() is None


def test_landing_on_a_folder_leaves_the_reader_where_they_were(application) -> None:
    """A folder is not a document, so choosing one reports no change."""
    tree = a_tree(BOTH)
    tree.topLevelItem(0).setExpanded(True)
    tree.setCurrentItem(tree.document_items()[1])
    announced: list[Document] = []
    tree.document_selected.connect(announced.append)

    tree.setCurrentItem(tree.topLevelItem(1))

    assert announced == []
    assert tree.selected_document() is not None


def test_the_selected_document_survives_the_library_being_read_again(
    application,
) -> None:
    tree = a_tree(BOTH)
    for item in tree.folder_items():
        item.setExpanded(True)
    tree.setCurrentItem(tree.document_items()[0])
    chosen = tree.selected_document()

    tree.show_library(BOTH)

    assert tree.selected_document() == chosen


def test_a_selection_inside_a_shut_folder_is_not_dragged_into_view(
    application,
) -> None:
    """Qt would open the folder to reach it, undoing the reader's own decision."""
    tree = a_tree(BOTH)
    for item in tree.folder_items():
        item.setExpanded(True)
    tree.setCurrentItem(tree.document_items()[0])
    chosen = tree.selected_document()

    shut = a_tree(BOTH)
    shut._selected = chosen
    shut.show_library(BOTH)

    assert [item.isExpanded() for item in shut.folder_items()] == [False, False, False]


def test_a_document_that_has_gone_since_selects_nothing(application) -> None:
    tree = a_tree(BOTH)
    tree.topLevelItem(0).setExpanded(True)
    tree.setCurrentItem(tree.document_items()[1])

    tree.show_library(Library((PLUGINS,)))

    assert tree.selected_document() is None


def test_an_empty_library_selects_nothing(application) -> None:
    tree = a_tree(Library())

    assert tree.selected_document() is None
    assert tree.document_items() == []


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


def test_clicking_a_folder_opens_and_closes_it(application) -> None:
    tree = a_tree(BOTH)
    folder = tree.topLevelItem(0)

    tree.itemClicked.emit(folder, FIRST_COLUMN)
    opened = folder.isExpanded()
    tree.itemClicked.emit(folder, FIRST_COLUMN)

    assert opened
    assert not folder.isExpanded()


def test_clicking_a_document_does_not_toggle_anything(application) -> None:
    tree = a_tree(BOTH)
    folder = tree.topLevelItem(0)
    folder.setExpanded(True)
    document_row = tree.document_items()[1]

    tree.itemClicked.emit(document_row, FIRST_COLUMN)

    assert folder.isExpanded()


def test_the_arrow_is_big_enough_to_read_as_a_control(application) -> None:
    """It is something you click, so it needs a target rather than a glyph.

    The figure is a stated minimum rather than a measurement: this harness has
    no real fonts, so its text metrics cannot be used to justify one. At the
    twelve pixels it began at, the arrow read as a speck.
    """
    tree = a_tree(BOTH)

    assert ARROW_PX >= MINIMUM_TARGET_PX
    assert tree.iconSize().width() == ARROW_PX
