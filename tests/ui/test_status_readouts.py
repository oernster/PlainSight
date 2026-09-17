"""The two standing readouts: what each says; when each says nothing."""

from __future__ import annotations

from PySide6.QtWidgets import QApplication

from plainsight.domain.document import Document, DocumentBody, DocumentKind
from plainsight.domain.extent import Extent
from plainsight.infrastructure.renderer import DocumentHtmlRenderer
from plainsight.ui.document_view import DocumentView
from plainsight.ui.main_window import MainWindow
from plainsight.ui.status_readouts import ExtentReadout, KindReadout
from plainsight.ui.theme import DARK, LIGHT, stylesheet

NO_DIVIDER = "QStatusBar::item {\n    border: none;\n}"
A_LONG_DOCUMENT = Extent(characters=24087, lines=438)
UNREADABLE = "This file is locked"


def select(window: MainWindow, row: int) -> None:
    """Open every folder, then choose one document, as a reader would."""
    for item in window.library_tree.folder_items():
        item.setExpanded(True)
    window.library_tree.setCurrentItem(window.library_tree.document_items()[row])


def counted(window: MainWindow) -> Extent:
    """What the document the reader has chosen actually holds."""
    document = window.library_tree.selected_document()
    assert document is not None
    return Extent.of(window.service.body_of(document).text)


def a_view(application: QApplication) -> DocumentView:
    view = DocumentView(DocumentHtmlRenderer(), DARK)
    view.show()
    QApplication.processEvents()
    return view


def a_document(**overrides: object) -> Document:
    fields: dict[str, object] = {
        "name": "SKILL.md",
        "path": "/skills/dev/SKILL.md",
        "kind": DocumentKind.MARKDOWN,
        "fingerprint": "500:1",
    }
    fields.update(overrides)
    return Document(**fields)  # type: ignore[arg-type]


def test_the_readout_words_a_count_the_way_an_editor_does(application) -> None:
    readout = ExtentReadout()

    readout.show_extent(A_LONG_DOCUMENT)

    assert readout.text() == "length: 24,087    lines: 438"


def test_the_readout_says_nothing_at_all_where_there_is_no_count(application) -> None:
    """Nothing rather than zeroes: no document is not a document of no words."""
    readout = ExtentReadout()
    readout.show_extent(A_LONG_DOCUMENT)

    readout.show_extent(None)

    assert readout.text() == ""


def test_a_chosen_document_is_counted_in_the_status_bar(window: MainWindow) -> None:
    select(window, 0)

    extent = counted(window)
    assert window.document_view.extent == extent
    assert window.extent_readout.text() == (
        f"length: {extent.characters:,}    lines: {extent.lines:,}"
    )


def test_choosing_another_document_counts_that_one_instead(
    window: MainWindow,
) -> None:
    select(window, 0)
    first = window.document_view.extent

    select(window, 1)

    assert first is not None
    assert window.document_view.extent == counted(window)


def test_nothing_is_counted_until_a_document_is_chosen(window: MainWindow) -> None:
    assert window.document_view.extent is None
    assert window.extent_readout.text() == ""


def test_a_re_read_that_changes_nothing_leaves_the_count_standing(
    window: MainWindow,
) -> None:
    """The library is re-read on every activation; the count must survive it."""
    select(window, 0)
    extent = window.document_view.extent

    window.refresh()

    assert extent is not None
    assert window.extent_readout.text() != ""
    assert window.document_view.extent == extent


def test_the_count_survives_a_change_of_appearance(window: MainWindow) -> None:
    """A redraw for colour reads the body again and must land on the same count."""
    select(window, 0)
    extent = window.document_view.extent

    window.switch_appearance()

    assert window.document_view.extent == extent


def test_a_document_that_could_not_be_read_is_not_counted(application) -> None:
    view = a_view(application)

    view.show_document(a_document(failure=UNREADABLE), lambda: DocumentBody())

    assert view.extent is None


def test_a_body_that_could_not_be_read_is_not_counted(application) -> None:
    view = a_view(application)

    view.show_document(a_document(), lambda: DocumentBody(failure=UNREADABLE))

    assert view.extent is None


def test_a_document_gone_since_it_was_listed_is_not_counted(application) -> None:
    view = a_view(application)

    view.show_document(a_document(), lambda: DocumentBody(text="   \n  "))

    assert view.extent is None


def test_the_count_is_of_the_text_rather_than_of_what_was_made_of_it(
    application,
) -> None:
    """Softening and rendering both change the markup; neither changes this."""
    text = "a wall of words. " * 300
    view = a_view(application)

    view.show_document(a_document(), lambda: DocumentBody(text=text))

    assert view.extent == Extent.of(text)


def test_a_standing_message_clears_whatever_was_counted(application) -> None:
    view = a_view(application)
    view.show_document(a_document(), lambda: DocumentBody(text="words"))

    view.show_nothing()

    assert view.extent is None


def test_the_kind_readout_names_the_kind(application) -> None:
    readout = KindReadout()

    readout.show_kind(DocumentKind.MARKDOWN)

    assert readout.text() == "Markdown document"


def test_the_kind_readout_says_nothing_while_no_document_is_open(
    application,
) -> None:
    readout = KindReadout()
    readout.show_kind(DocumentKind.PDF)

    readout.show_kind(None)

    assert readout.text() == ""


def test_a_chosen_document_is_named_in_the_status_bar(window: MainWindow) -> None:
    select(window, 0)

    assert window.kind_readout.text() == "Markdown document"


def test_nothing_is_named_until_a_document_is_chosen(window: MainWindow) -> None:
    assert window.kind_readout.text() == ""


def test_a_document_that_could_not_be_read_is_still_named(window: MainWindow) -> None:
    """The kind comes from the file name, so no reading is needed to know it."""
    window.show_document(a_document(failure=UNREADABLE, kind=DocumentKind.PDF))

    assert window.kind_readout.text() == "PDF document"
    assert window.extent_readout.text() == ""


def test_every_kind_is_named_where_a_reader_would_meet_it(application) -> None:
    """A kind added without a name would reach the status bar as a blank."""
    readout = KindReadout()

    for kind in DocumentKind:
        readout.show_kind(kind)
        assert readout.text().strip() != ""


def test_a_message_takes_the_left_end_and_the_kind_returns_after_it(
    window: MainWindow,
) -> None:
    """The message is the more urgent of the two, so it gets the room.

    Measured rather than assumed: the status bar hides an ordinary widget for
    as long as it is saying something, which is why the kind sits there and the
    count does not.
    """
    select(window, 0)

    window.report_status("Could not start the editor")

    assert not window.kind_readout.isVisible()
    assert window.kind_readout.text() == "Markdown document"
    assert window.extent_readout.isVisible()


def test_neither_appearance_draws_a_divider_after_the_kind() -> None:
    """Measured: the style drew one hard against the last letter.

    It read as a text cursor parked in the status bar. The rule that takes
    it away is asserted here so an edit to the stylesheet cannot quietly
    bring it back.
    """
    wanted = NO_DIVIDER

    for palette in (DARK, LIGHT):
        assert wanted in stylesheet(palette)
