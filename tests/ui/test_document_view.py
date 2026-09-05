"""The reading pane: where a long frontmatter value lands and how it is left.

The pane is driven with real key events through a real QApplication, because a
jump that never reaches the widget is exactly the failure being guarded against.
"""

from __future__ import annotations

from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QKeyEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from plainsight.domain.document import HEADER_FIELD_LIMIT, Document, DocumentKind
from plainsight.infrastructure.renderer import DocumentHtmlRenderer
from plainsight.ui.auto_scroller import START_HOLD_MS, TICK_MS, Phase
from plainsight.ui.document_view import GONE_SINCE_LISTED, DocumentView
from plainsight.ui.theme import DARK, LIGHT

BODY_MARKER = "the body of the document"
DEFAULT_BODY = f"# Heading\n\n{BODY_MARKER}\n\n" + ("more words. " * 400)
WALL = "w" * (HEADER_FIELD_LIMIT + 1)
VIEW_WIDTH_PX = 600
VIEW_HEIGHT_PX = 300
START_HOLD_TICKS = START_HOLD_MS // TICK_MS
HALF = 2


def a_view(application: QApplication) -> DocumentView:
    view = DocumentView(DocumentHtmlRenderer(), DARK)
    view.resize(VIEW_WIDTH_PX, VIEW_HEIGHT_PX)
    view.show()
    QApplication.processEvents()
    return view


def a_document(**overrides: object) -> Document:
    fields: dict[str, object] = {
        "name": "SKILL.md",
        "path": "/skills/dev/SKILL.md",
        "kind": DocumentKind.MARKDOWN,
        "declared_name": "dev",
        "description": "engineering",
        "fingerprint": "500:1",
    }
    fields.update(overrides)
    return Document(**fields)  # type: ignore[arg-type]


def show(view: DocumentView, document: Document, body: str = DEFAULT_BODY) -> None:
    """Show a document, its body coming from the test rather than from disk.

    The pane asks for a body only where it is actually going to redraw, so a
    test that passes one is also saying a redraw was expected.
    """
    view.show_document(document, lambda: body)


def press(view: DocumentView, key: Qt.Key, modifier: Qt.KeyboardModifier) -> None:
    view.setFocus()
    QApplication.processEvents()
    QApplication.sendEvent(view, QKeyEvent(QEvent.Type.KeyPress, key, modifier))


def test_a_long_field_follows_the_body_rather_than_heading_it(application) -> None:
    view = a_view(application)

    show(view, a_document(declared_fields=(("revision_note", WALL),)))

    text = view.toPlainText()
    assert text.index("revision_note") > text.index(BODY_MARKER)


def test_a_short_field_stays_in_the_header(application) -> None:
    view = a_view(application)

    show(view, a_document(declared_fields=(("source", "a short line"),)))

    text = view.toPlainText()
    assert text.index("source") < text.index(BODY_MARKER)


def test_a_document_with_no_long_field_gains_no_trailing_section(application) -> None:
    view = a_view(application)

    show(view, a_document(declared_fields=(("source", "a short line"),)))

    assert view.toPlainText().rstrip().endswith("more words.")


def test_the_heading_is_the_name_the_document_declares(application) -> None:
    view = a_view(application)

    show(view, a_document())

    assert view.toPlainText().startswith("dev")


def test_a_document_declaring_nothing_is_headed_by_its_file_name(
    application,
) -> None:
    view = a_view(application)

    show(view, a_document(declared_name="", description=""))

    assert view.toPlainText().startswith("SKILL.md")


def test_plain_text_reaches_the_page_exactly_as_it_was_typed(application) -> None:
    """Neither softened nor laid out: its line breaks are the author's own."""
    typed = "Shopping\n--------\n* milk\n* eggs\n"
    view = a_view(application)

    show(
        view,
        a_document(
            name="shopping.txt",
            path="/notes/shopping.txt",
            kind=DocumentKind.PLAIN_TEXT,
            declared_name="",
            description="",
            declared_fields=(),
        ),
        typed,
    )

    assert typed.strip() in view.toPlainText()


def test_control_home_returns_to_the_top(application) -> None:
    view = a_view(application)
    show(view, a_document())
    bar = view.verticalScrollBar()
    bar.setValue(bar.maximum() // HALF)
    assert bar.value() > 0

    press(view, Qt.Key.Key_Home, Qt.KeyboardModifier.ControlModifier)

    assert bar.value() == 0


def test_home_alone_returns_to_the_top(application) -> None:
    view = a_view(application)
    show(view, a_document())
    bar = view.verticalScrollBar()
    bar.setValue(bar.maximum())

    press(view, Qt.Key.Key_Home, Qt.KeyboardModifier.NoModifier)

    assert bar.value() == 0


def test_control_end_travels_to_the_foot_of_the_page(application) -> None:
    """Qt leaves this chord unhandled, so it is the pane that must answer."""
    view = a_view(application)
    show(view, a_document())
    bar = view.verticalScrollBar()

    press(view, Qt.Key.Key_End, Qt.KeyboardModifier.ControlModifier)

    assert bar.value() == bar.maximum()


def test_end_travels_to_the_foot_of_the_page(application) -> None:
    view = a_view(application)
    show(view, a_document())
    bar = view.verticalScrollBar()

    press(view, Qt.Key.Key_End, Qt.KeyboardModifier.NoModifier)

    assert bar.value() == bar.maximum()


def test_a_jump_holds_rather_than_being_carried_back_down(application) -> None:
    view = a_view(application)
    show(view, a_document())
    for _ in range(START_HOLD_TICKS + 1):
        view.scroller.tick()
    assert view.scroller.phase is Phase.DOWN

    press(view, Qt.Key.Key_End, Qt.KeyboardModifier.NoModifier)

    assert view.scroller.phase is Phase.MANUAL


def test_an_unhandled_key_is_left_to_the_toolkit(application) -> None:
    view = a_view(application)
    show(view, a_document())
    bar = view.verticalScrollBar()
    bar.setValue(bar.maximum())

    press(view, Qt.Key.Key_A, Qt.KeyboardModifier.NoModifier)

    assert bar.value() == bar.maximum()


def test_clicking_the_text_focuses_the_pane_it_is_in(application) -> None:
    """Tab alone was the whole of it, so the keys went somewhere else."""
    view = a_view(application)
    show(view, a_document())
    QApplication.processEvents()

    QTest.mouseClick(view.viewport(), Qt.MouseButton.LeftButton)

    assert QApplication.focusWidget() is view


def test_a_page_that_fits_still_takes_no_click(application) -> None:
    view = a_view(application)
    view.setHtml("<p>short</p>")
    view.sync_focus_policy()

    assert view.focusPolicy() is Qt.FocusPolicy.NoFocus


def test_showing_the_same_document_again_leaves_the_reader_where_they_were(
    application,
) -> None:
    """The library is re-read on every activation; that must not lose the place."""
    view = a_view(application)
    document = a_document()
    show(view, document)
    bar = view.verticalScrollBar()
    bar.setValue(bar.maximum() // HALF)
    reached = bar.value()

    show(view, a_document())

    assert reached > 0
    assert bar.value() == reached


def test_a_document_edited_on_disk_is_drawn_again(application) -> None:
    view = a_view(application)
    show(view, a_document())
    bar = view.verticalScrollBar()
    bar.setValue(bar.maximum() // HALF)

    show(
        view,
        a_document(fingerprint="900:2"),
        "# Changed\n\n" + ("other words. " * 400),
    )

    assert bar.value() == 0


def test_a_document_left_alone_is_never_read_off_disk_again(application) -> None:
    """Laziness is only real if the unchanged case asks for nothing.

    The library is re-read on every activation. A pane that asked for a body
    each time would read every opened file again on every return to the
    window, which is the work fetching a body on opening exists to avoid.
    """
    view = a_view(application)
    asked: list[str] = []

    def read_body() -> str:
        asked.append("asked")
        return DEFAULT_BODY

    view.show_document(a_document(), read_body)
    view.show_document(a_document(), read_body)
    view.show_document(a_document(), read_body)

    assert len(asked) == 1


def test_a_document_that_went_away_says_so_rather_than_showing_a_blank(
    application,
) -> None:
    """Listed a moment ago, gone by the time it was opened."""
    view = a_view(application)

    show(view, a_document(), "")

    assert GONE_SINCE_LISTED in view.toPlainText()


def test_a_change_of_palette_draws_the_same_document_again(application) -> None:
    view = a_view(application)
    document = a_document()
    show(view, document)
    bar = view.verticalScrollBar()
    bar.setValue(bar.maximum() // HALF)

    view.wear(LIGHT)
    show(view, document)

    assert bar.value() == 0
