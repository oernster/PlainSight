"""The reading pane: where a long frontmatter value lands and how it is left.

The pane is driven with real key events through a real QApplication, because a
jump that never reaches the widget is exactly the failure being guarded against.
"""

from __future__ import annotations

from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QKeyEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from skillsviewer.domain.skill import HEADER_FIELD_LIMIT, Skill
from skillsviewer.infrastructure.markdown_renderer import PythonMarkdownRenderer
from skillsviewer.ui.auto_scroller import START_HOLD_MS, TICK_MS, Phase
from skillsviewer.ui.skill_view import SkillView
from skillsviewer.ui.theme import DARK, LIGHT

BODY_MARKER = "the body of the skill"
WALL = "w" * (HEADER_FIELD_LIMIT + 1)
VIEW_WIDTH_PX = 600
VIEW_HEIGHT_PX = 300
START_HOLD_TICKS = START_HOLD_MS // TICK_MS
HALF = 2


def a_view(application: QApplication) -> SkillView:
    view = SkillView(PythonMarkdownRenderer(), DARK)
    view.resize(VIEW_WIDTH_PX, VIEW_HEIGHT_PX)
    view.show()
    QApplication.processEvents()
    return view


def a_skill(**overrides: object) -> Skill:
    fields: dict[str, object] = {
        "name": "dev",
        "description": "engineering",
        "directory": "/skills/dev",
        "document_path": "/skills/dev/SKILL.md",
        "body": f"# Heading\n\n{BODY_MARKER}\n\n" + ("more words. " * 400),
    }
    fields.update(overrides)
    return Skill(**fields)  # type: ignore[arg-type]


def press(view: SkillView, key: Qt.Key, modifier: Qt.KeyboardModifier) -> None:
    view.setFocus()
    QApplication.processEvents()
    QApplication.sendEvent(view, QKeyEvent(QEvent.Type.KeyPress, key, modifier))


def test_a_long_field_follows_the_body_rather_than_heading_it(application) -> None:
    view = a_view(application)

    view.show_skill(a_skill(declared_fields=(("revision_note", WALL),)))

    text = view.toPlainText()
    assert text.index("revision_note") > text.index(BODY_MARKER)


def test_a_short_field_stays_in_the_header(application) -> None:
    view = a_view(application)

    view.show_skill(a_skill(declared_fields=(("source", "a short line"),)))

    text = view.toPlainText()
    assert text.index("source") < text.index(BODY_MARKER)


def test_a_skill_with_no_long_field_gains_no_trailing_section(application) -> None:
    view = a_view(application)

    view.show_skill(a_skill(declared_fields=(("source", "a short line"),)))

    assert view.toPlainText().rstrip().endswith("more words.")


def test_control_home_returns_to_the_top(application) -> None:
    view = a_view(application)
    view.show_skill(a_skill())
    bar = view.verticalScrollBar()
    bar.setValue(bar.maximum() // HALF)
    assert bar.value() > 0

    press(view, Qt.Key.Key_Home, Qt.KeyboardModifier.ControlModifier)

    assert bar.value() == 0


def test_home_alone_returns_to_the_top(application) -> None:
    view = a_view(application)
    view.show_skill(a_skill())
    bar = view.verticalScrollBar()
    bar.setValue(bar.maximum())

    press(view, Qt.Key.Key_Home, Qt.KeyboardModifier.NoModifier)

    assert bar.value() == 0


def test_control_end_travels_to_the_foot_of_the_page(application) -> None:
    """Qt leaves this chord unhandled, so it is the pane that must answer."""
    view = a_view(application)
    view.show_skill(a_skill())
    bar = view.verticalScrollBar()

    press(view, Qt.Key.Key_End, Qt.KeyboardModifier.ControlModifier)

    assert bar.value() == bar.maximum()


def test_end_travels_to_the_foot_of_the_page(application) -> None:
    view = a_view(application)
    view.show_skill(a_skill())
    bar = view.verticalScrollBar()

    press(view, Qt.Key.Key_End, Qt.KeyboardModifier.NoModifier)

    assert bar.value() == bar.maximum()


def test_a_jump_holds_rather_than_being_carried_back_down(application) -> None:
    view = a_view(application)
    view.show_skill(a_skill())
    for _ in range(START_HOLD_TICKS + 1):
        view.scroller.tick()
    assert view.scroller.phase is Phase.DOWN

    press(view, Qt.Key.Key_End, Qt.KeyboardModifier.NoModifier)

    assert view.scroller.phase is Phase.MANUAL


def test_an_unhandled_key_is_left_to_the_toolkit(application) -> None:
    view = a_view(application)
    view.show_skill(a_skill())
    bar = view.verticalScrollBar()
    bar.setValue(bar.maximum())

    press(view, Qt.Key.Key_A, Qt.KeyboardModifier.NoModifier)

    assert bar.value() == bar.maximum()


def test_clicking_the_text_focuses_the_pane_it_is_in(application) -> None:
    """Tab alone was the whole of it, so the keys went somewhere else."""
    view = a_view(application)
    view.show_skill(a_skill())
    QApplication.processEvents()

    QTest.mouseClick(view.viewport(), Qt.MouseButton.LeftButton)

    assert QApplication.focusWidget() is view


def test_a_page_that_fits_still_takes_no_click(application) -> None:
    view = a_view(application)
    view.setHtml("<p>short</p>")
    view.sync_focus_policy()

    assert view.focusPolicy() is Qt.FocusPolicy.NoFocus


def test_showing_the_same_skill_again_leaves_the_reader_where_they_were(
    application,
) -> None:
    """The library is re-read on every activation; that must not lose the place."""
    view = a_view(application)
    skill = a_skill()
    view.show_skill(skill)
    bar = view.verticalScrollBar()
    bar.setValue(bar.maximum() // HALF)
    reached = bar.value()

    view.show_skill(a_skill())

    assert reached > 0
    assert bar.value() == reached


def test_a_skill_edited_on_disk_is_drawn_again(application) -> None:
    view = a_view(application)
    view.show_skill(a_skill())
    bar = view.verticalScrollBar()
    bar.setValue(bar.maximum() // HALF)

    view.show_skill(a_skill(body="# Changed\n\n" + ("other words. " * 400)))

    assert bar.value() == 0


def test_a_change_of_palette_draws_the_same_skill_again(application) -> None:
    view = a_view(application)
    skill = a_skill()
    view.show_skill(skill)
    bar = view.verticalScrollBar()
    bar.setValue(bar.maximum() // HALF)

    view.wear(LIGHT)
    view.show_skill(skill)

    assert bar.value() == 0
