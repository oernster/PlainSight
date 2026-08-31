"""Keeping the reader's place when the page is redrawn under them."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from PySide6.QtCore import QPoint
from PySide6.QtWidgets import QApplication

from skillsviewer.application.services import SkillLibraryService
from skillsviewer.domain.settings import Settings
from skillsviewer.infrastructure.markdown_renderer import PythonMarkdownRenderer
from skillsviewer.infrastructure.resources import BundledAssets
from skillsviewer.infrastructure.skill_repository import FileSystemSkillRepository
from skillsviewer.ui.main_window import MainWindow
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
    store.settings = Settings(skills_root=str(long_root))
    service = SkillLibraryService(
        repository=FileSystemSkillRepository(),
        settings_store=store,
        launcher=FakeLauncher(),
        opener=FakeOpener(),
        probe=FakeProbe(),
        paths=FakePaths(),
    )
    window = MainWindow(service, PythonMarkdownRenderer(), BundledAssets())
    window.resize(WIDE_PX, TALL_PX)
    window.show()
    QApplication.processEvents()
    window.show_skill(_skill(window, "long"))
    QApplication.processEvents()
    yield window
    window.close()
    window.deleteLater()
    QApplication.processEvents()


def _skill(window: MainWindow, name: str) -> object:
    for skill in window._service.load().skills:
        if skill.name == name:
            return skill
    raise AssertionError(f"no skill named {name}")


def top_character(window: MainWindow) -> int:
    """Where in the text the first visible character sits."""
    return window.skill_view.cursorForPosition(TOP_LEFT).position()


def glimpse(window: MainWindow) -> str:
    """The words at the top of the page, for a failure that reads plainly."""
    start = top_character(window)
    return window.skill_view.toPlainText()[start : start + GLIMPSE]


def scroll_halfway(window: MainWindow) -> None:
    bar = window.skill_view.verticalScrollBar()
    assert bar.maximum() > AT_THE_TOP, "the fixture skill has to actually scroll"
    bar.setValue(bar.maximum() // 2)
    QApplication.processEvents()


def test_switching_appearance_leaves_the_reader_exactly_where_they_were(
    reading: MainWindow,
) -> None:
    """The reported defect: dark mode used to throw the page back to the top."""
    scroll_halfway(reading)
    before = top_character(reading)

    reading.switch_appearance()
    QApplication.processEvents()

    assert top_character(reading) == before
    assert reading.skill_view.verticalScrollBar().value() > AT_THE_TOP


def test_switching_back_again_holds_the_place_too(reading: MainWindow) -> None:
    scroll_halfway(reading)
    before = top_character(reading)

    reading.switch_appearance()
    QApplication.processEvents()
    reading.switch_appearance()
    QApplication.processEvents()

    assert top_character(reading) == before


def test_changing_the_text_size_keeps_the_reader_on_the_same_words(
    reading: MainWindow,
) -> None:
    """The words, not the pixel: a new size reflows the page beneath them."""
    scroll_halfway(reading)
    before = top_character(reading)

    reading.cycle_font_size()
    QApplication.processEvents()

    assert abs(top_character(reading) - before) <= A_PARAGRAPH, glimpse(reading)
    assert reading.skill_view.verticalScrollBar().value() > AT_THE_TOP


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

    assert reading.skill_view.verticalScrollBar().value() == AT_THE_TOP


def test_a_different_skill_still_opens_at_its_beginning(
    reading: MainWindow,
) -> None:
    """Keeping a place must never leak across to a page nobody was reading."""
    scroll_halfway(reading)

    reading.show_skill(_skill(reading, "short"))
    QApplication.processEvents()
    reading.show_skill(_skill(reading, "long"))
    QApplication.processEvents()

    assert reading.skill_view.verticalScrollBar().value() == AT_THE_TOP


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
    view = reading.skill_view
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
    """A remembered place must not survive into a different document.

    It holds by construction rather than by a guard: drawing any page spends
    the kept place; the empty state is too short to scroll in any case.
    Written down so that stops being an accident.
    """
    scroll_halfway(reading)
    reading.skill_view.remember_place()

    reading.skill_view.show_empty_root()
    QApplication.processEvents()

    assert reading.skill_view.verticalScrollBar().value() == AT_THE_TOP
    assert reading.skill_view._resuming is None


def test_the_same_holds_when_nothing_is_selected(reading: MainWindow) -> None:
    scroll_halfway(reading)
    reading.skill_view.remember_place()

    reading.skill_view.show_nothing()
    QApplication.processEvents()

    assert reading.skill_view.verticalScrollBar().value() == AT_THE_TOP
    assert reading.skill_view._resuming is None


def test_the_place_is_restored_again_once_the_page_has_settled(
    reading: MainWindow,
) -> None:
    """The second pass is what makes this safe on a real machine.

    A document still laying out reports a zero rect for a block it has not
    placed, and zero against a bar that setHtml has just reset is the top of
    the page. That state is arranged here directly, because a harness lays out
    synchronously and so never reaches it on its own.
    """
    scroll_halfway(reading)
    view = reading.skill_view
    before = top_character(reading)

    view._settling = before
    view.verticalScrollBar().setValue(AT_THE_TOP)
    view._resume_when_settled()

    assert top_character(reading) == before
    assert view._settling is None
