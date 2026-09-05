"""Keeping the reader's place when the page is redrawn under them."""

from __future__ import annotations

import pathlib
from collections.abc import Iterator
from pathlib import Path

import pytest
from PySide6.QtCore import QPoint
from PySide6.QtWidgets import QApplication

from plainsight.__main__ import build_readers
from plainsight.application.services import LibraryService
from plainsight.domain.settings import Settings
from plainsight.infrastructure.document_repository import FileSystemDocumentRepository
from plainsight.infrastructure.renderer import DocumentHtmlRenderer
from plainsight.infrastructure.resources import BundledAssets
from plainsight.ui.auto_scroller import Phase
from plainsight.ui.document_view import Place
from plainsight.ui.library_tree import DOCUMENT_ROLE, FIRST_COLUMN
from plainsight.ui.main_window import MainWindow
from tests.application.fakes import (
    FakeLauncher,
    FakeOpener,
    FakePaths,
    FakeProbe,
    FakeSettingsStore,
)

WIDE_PX = 1100
# Wide enough that the column is genuinely capped and the margins are real.
# Narrower than the column it wants, a pane has no margin to change.
VERY_WIDE_PX = 2400
TALL_PX = 760
TOP_LEFT = QPoint(0, 0)
AT_THE_TOP = 0
PARAGRAPHS = 200
# Enough of the text to name which paragraph the reader is looking at.
GLIMPSE = 24

A_LONG_SKILL = """---
name: {name}
description: a skill long enough to scroll
---

# {name}

{body}
"""


def a_paragraph(number: int) -> str:
    return (
        f"Paragraph {number} with a fair amount of text in it, so that the page "
        f"is genuinely longer than the window that shows it."
    )


def a_long_body() -> str:
    return "\n\n".join(a_paragraph(number) for number in range(PARAGRAPHS))


# How far the top of the page may honestly move when the text reflows. At a new
# size the lines break elsewhere, so the same place is the same paragraph rather
# than the same character; a move beyond one paragraph is a jump.
A_PARAGRAPH = len(a_paragraph(0))


@pytest.fixture
def long_root(tmp_path: Path) -> Path:
    """A library holding one skill and a short one, both real on disk."""
    root = tmp_path / "skills"
    for name, body in (("long", a_long_body()), ("short", "One line.")):
        directory = root / name
        directory.mkdir(parents=True)
        (directory / "SKILL.md").write_text(
            A_LONG_SKILL.format(name=name, body=body), encoding="utf-8"
        )
    return root


@pytest.fixture
def reading(
    application: QApplication, long_root: Path, store: FakeSettingsStore
) -> Iterator[MainWindow]:
    """A window already part way down a long skill."""
    store.settings = Settings(documents_root=str(long_root))
    service = LibraryService(
        repository=FileSystemDocumentRepository(build_readers()),
        settings_store=store,
        launcher=FakeLauncher(),
        opener=FakeOpener(),
        probe=FakeProbe(),
        paths=FakePaths(),
    )
    window = MainWindow(service, DocumentHtmlRenderer(), BundledAssets())
    window.resize(WIDE_PX, TALL_PX)
    window.show()
    QApplication.processEvents()
    _select(window, "long")
    QApplication.processEvents()
    yield window
    window.close()
    window.deleteLater()
    QApplication.processEvents()


def _select(window: MainWindow, folder: str) -> None:
    """Choose the one document inside the named folder, through the tree.

    Through the tree rather than by calling the window directly, because the
    window re-renders from whatever the tree has selected: a page pushed in
    behind the tree is wiped the moment anything asks for a repaint.
    """
    for item in window.library_tree.folder_items():
        item.setExpanded(True)
    for item in window.library_tree.document_items():
        document = item.data(FIRST_COLUMN, DOCUMENT_ROLE)
        if pathlib.PurePath(document.path).parent.name == folder:
            window.library_tree.setCurrentItem(item)
            return
    raise AssertionError(f"no document in a folder named {folder}")


def top_character(window: MainWindow) -> int:
    """Where in the text the first visible character sits."""
    return window.document_view.cursorForPosition(TOP_LEFT).position()


def glimpse(window: MainWindow) -> str:
    """The words at the top of the page, for a failure that reads plainly."""
    start = top_character(window)
    return window.document_view.toPlainText()[start : start + GLIMPSE]


TICKS_TO_START = 2000
SETTLE_MS = 400
SETTLE_STEP_MS = 20


def settle(window: MainWindow) -> None:
    """Run the loop until the page has stopped changing shape.

    The exact place is put back when the page returns to the height it had,
    which is announced a turn or two after the redraw rather than during it.
    """
    from PySide6.QtTest import QTest

    for _step in range(SETTLE_MS // SETTLE_STEP_MS):
        QApplication.processEvents()
        QTest.qWait(SETTLE_STEP_MS)


def scroll_halfway(window: MainWindow) -> None:
    bar = window.document_view.verticalScrollBar()
    assert bar.maximum() > AT_THE_TOP, "the fixture skill has to actually scroll"
    bar.setValue(bar.maximum() // 2)
    QApplication.processEvents()


def test_switching_appearance_leaves_the_reader_exactly_where_they_were(
    reading: MainWindow,
) -> None:
    """The reported defect: dark mode used to throw the page back to the top."""
    scroll_halfway(reading)
    before = top_character(reading)
    before_pixel = reading.document_view.verticalScrollBar().value()
    before_height = reading.document_view.verticalScrollBar().maximum()

    reading.switch_appearance()
    settle(reading)

    # The words, exactly. The pixel is exact too wherever the page comes back
    # to the height it had, which is what a change of colour normally does.
    bar = reading.document_view.verticalScrollBar()
    if bar.maximum() == before_height:
        # The page came back to the height it had, so the place taken is valid
        # again and goes back untouched. This is the ordinary case.
        assert bar.value() == before_pixel
        assert top_character(reading) == before
    else:
        # It kept a different height, so the words are followed instead and the
        # line may break a little either side of where it did.
        assert abs(top_character(reading) - before) <= A_PARAGRAPH, glimpse(reading)
    assert bar.value() > AT_THE_TOP


def test_switching_back_again_holds_the_place_too(reading: MainWindow) -> None:
    scroll_halfway(reading)
    before = top_character(reading)

    reading.switch_appearance()
    QApplication.processEvents()
    reading.switch_appearance()
    QApplication.processEvents()

    assert abs(top_character(reading) - before) <= A_PARAGRAPH, glimpse(reading)
    assert reading.document_view.verticalScrollBar().value() > AT_THE_TOP


def test_changing_the_text_size_keeps_the_reader_on_the_same_words(
    reading: MainWindow,
) -> None:
    """The words, not the pixel: a new size reflows the page beneath them."""
    scroll_halfway(reading)
    before = top_character(reading)

    reading.cycle_font_size()
    QApplication.processEvents()

    assert abs(top_character(reading) - before) <= A_PARAGRAPH, glimpse(reading)
    assert reading.document_view.verticalScrollBar().value() > AT_THE_TOP


def test_the_place_is_held_through_every_size_in_the_cycle(
    reading: MainWindow,
) -> None:
    scroll_halfway(reading)
    before = top_character(reading)

    for _step in range(3):
        reading.cycle_font_size()
        QApplication.processEvents()

    assert abs(top_character(reading) - before) <= A_PARAGRAPH, glimpse(reading)


def test_a_reader_at_the_top_stays_at_the_top(reading: MainWindow) -> None:
    reading.switch_appearance()
    QApplication.processEvents()

    assert reading.document_view.verticalScrollBar().value() == AT_THE_TOP


def test_a_different_skill_still_opens_at_its_beginning(
    reading: MainWindow,
) -> None:
    """Keeping a place must never leak across to a page nobody was reading."""
    scroll_halfway(reading)

    _select(reading, "short")
    QApplication.processEvents()
    _select(reading, "long")
    QApplication.processEvents()

    assert reading.document_view.verticalScrollBar().value() == AT_THE_TOP


def test_the_column_is_re_measured_when_the_text_grows(
    reading: MainWindow,
) -> None:
    """A column counted in characters holds fewer pixels at a larger size.

    This already held before the text sizes existed: changing the stylesheet
    resizes the pane; a resize is what triggers the measurement. It is written
    down because nothing else said so, then because a column that stopped
    following the font would be a silent regression rather than a visible
    break.
    """
    reading.resize(VERY_WIDE_PX, TALL_PX)
    QApplication.processEvents()
    view = reading.document_view
    wanted_before = view.readable_width()
    margin_before = view.viewportMargins().left()
    assert margin_before > AT_THE_TOP, "the window has to be wider than the column"

    reading.cycle_font_size()
    QApplication.processEvents()

    # The column the font now wants is wider, so the margins holding it must
    # have narrowed. Comparing the margin is the point: the wanted width is a
    # function of the font and grows whether or not anything acts on it.
    assert view.readable_width() > wanted_before
    assert view.viewportMargins().left() < margin_before


def test_a_place_taken_is_never_spent_on_a_page_nobody_was_reading(
    reading: MainWindow,
) -> None:
    """A remembered place must not survive into a different document."""
    scroll_halfway(reading)
    reading.document_view.remember_place()

    reading.document_view.show_empty_root()
    QApplication.processEvents()

    assert reading.document_view.verticalScrollBar().value() == AT_THE_TOP
    assert reading.document_view._place is None


def test_the_same_holds_when_nothing_is_selected(reading: MainWindow) -> None:
    scroll_halfway(reading)
    reading.document_view.remember_place()

    reading.document_view.show_nothing()
    QApplication.processEvents()

    assert reading.document_view.verticalScrollBar().value() == AT_THE_TOP
    assert reading.document_view._place is None


def test_nothing_is_remembered_from_the_top_of_a_page(reading: MainWindow) -> None:
    reading.document_view.remember_place()

    assert reading.document_view._place is None


def test_the_page_is_laid_out_before_it_is_ever_shown(reading: MainWindow) -> None:
    """The heart of it: there is no moment when the page has no shape.

    Every earlier attempt put the position back after the text had been set,
    which is after the position was already gone. A document laid out before it
    is attached never opens that gap, so nothing has to be timed.
    """
    scroll_halfway(reading)
    before = top_character(reading)

    reading.switch_appearance()
    # Deliberately no processEvents: if this needed the event loop to come
    # right, it would be a race rather than a fix. The tolerance is a line
    # rather than a character, since the scroll range does move a little and
    # the return then follows the words; what is asserted is that the reader is
    # still where they were reading, not at the top.
    assert abs(top_character(reading) - before) <= A_PARAGRAPH, glimpse(reading)
    assert reading.document_view.verticalScrollBar().value() > AT_THE_TOP


def test_the_reading_cycle_holds_still_for_a_moment_after_a_switch(
    reading: MainWindow,
) -> None:
    """The page has just changed shape; reading on through that gives the
    reader a moving target while it settles.

    The cycle has to be under way first. Before it has started there is nothing
    to pause, which is why the hold is asked for rather than forced.
    """
    scroll_halfway(reading)
    scroller = reading.document_view.scroller
    for _tick in range(TICKS_TO_START):
        scroller.tick()
        if scroller.phase is Phase.DOWN:
            break
    assert scroller.phase is Phase.DOWN, "the page never began reading itself"

    reading.switch_appearance()
    QApplication.processEvents()

    assert scroller.phase is Phase.MANUAL


def test_a_redraw_that_keeps_the_height_puts_the_pixel_back_exactly(
    reading: MainWindow,
) -> None:
    """The rule the exactness rests on, stated on its own.

    A change of colour alters no text, so the page returns to the height it
    had; the position taken then is valid again and is applied unchanged.
    """
    scroll_halfway(reading)
    view = reading.document_view
    bar = view.verticalScrollBar()
    wanted = Place(pixel=bar.value(), height=bar.maximum(), character=0)
    bar.setValue(AT_THE_TOP)

    view._return_to(wanted)

    assert bar.value() == wanted.pixel
