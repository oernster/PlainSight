"""The library tree: its headings, its arrows and what a heading does not do."""

from __future__ import annotations

from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import QApplication

from skillsviewer.domain.catalogue import SkillCatalogue
from skillsviewer.domain.origin import SkillOrigin
from skillsviewer.domain.skill import Skill
from skillsviewer.ui.skill_tree import ARROW_PX, FIRST_COLUMN, SkillTree, arrow_icon
from skillsviewer.ui.theme import DARK, LIGHT

BOTH_GROUPS = 2
MINIMUM_TARGET_PX = 20


def a_skill(name: str, origin: SkillOrigin, plugin: str = "") -> Skill:
    return Skill(
        name=name,
        description="about " + name,
        directory=f"/d/{name}",
        document_path=f"/d/{name}/SKILL.md",
        body="Body.",
        origin=origin,
        source_name=plugin,
    )


MINE = a_skill("prose", SkillOrigin.PERSONAL)
THEIRS = a_skill("hookify", SkillOrigin.PLUGIN, "hookify")
MIXED = SkillCatalogue.of([MINE, THEIRS])
ONLY_MINE = SkillCatalogue.of([MINE])


def a_tree(application: QApplication, catalogue: SkillCatalogue) -> SkillTree:
    tree = SkillTree(DARK)
    tree.show_catalogue(catalogue)
    tree.show()
    QApplication.processEvents()
    return tree


def press(tree: SkillTree, key: Qt.Key) -> None:
    QApplication.sendEvent(
        tree, QKeyEvent(QEvent.Type.KeyPress, key, Qt.KeyboardModifier.NoModifier)
    )


def test_two_origins_are_shown_under_a_heading_each(application) -> None:
    tree = a_tree(application, MIXED)

    headings = [item.text(FIRST_COLUMN) for item in tree.headings()]

    assert headings == ["Your skills (1)", "Plugin skills (1)"]


def test_one_origin_is_shown_flat_with_no_heading_at_all(application) -> None:
    """Nothing to separate means no grouping the user did not ask for."""
    tree = a_tree(application, ONLY_MINE)

    assert tree.headings() == []
    assert [item.text(FIRST_COLUMN) for item in tree.skill_items()] == ["prose"]


def test_a_plugin_row_says_which_plugin_it_came_with(application) -> None:
    tree = a_tree(application, MIXED)

    labels = [item.text(FIRST_COLUMN) for item in tree.skill_items()]

    assert "hookify (hookify)" in labels


def test_every_group_opens_shut(application) -> None:
    """A library of fifty is a wall of rows; it opens as a short list instead."""
    tree = a_tree(application, MIXED)

    assert [item.isExpanded() for item in tree.headings()] == [False, False]


def test_a_group_the_reader_left_open_opens_open(application) -> None:
    tree = SkillTree(DARK, (SkillOrigin.PLUGIN.label,))
    tree.show_catalogue(MIXED)
    tree.show()
    QApplication.processEvents()

    assert [item.isExpanded() for item in tree.headings()] == [False, True]


def test_opening_and_shutting_a_group_is_reported_for_remembering(
    application,
) -> None:
    tree = a_tree(application, MIXED)
    reported: list[tuple] = []
    tree.groups_changed.connect(reported.append)
    heading = tree.headings()[0]

    heading.setExpanded(True)
    heading.setExpanded(False)

    assert reported == [(SkillOrigin.PERSONAL.label,), ()]


def test_enter_opens_a_heading_and_shuts_it_again(application) -> None:
    tree = a_tree(application, MIXED)
    heading = tree.headings()[0]
    tree.setCurrentItem(heading)

    press(tree, Qt.Key.Key_Return)
    opened = heading.isExpanded()
    press(tree, Qt.Key.Key_Return)

    assert opened
    assert not heading.isExpanded()


def test_space_toggles_a_heading_too(application) -> None:
    tree = a_tree(application, MIXED)
    heading = tree.headings()[0]
    tree.setCurrentItem(heading)

    press(tree, Qt.Key.Key_Space)

    assert heading.isExpanded()


def test_a_heading_the_reader_opened_stays_open_on_a_re_read(
    application,
) -> None:
    tree = a_tree(application, MIXED)
    tree.headings()[0].setExpanded(True)

    tree.show_catalogue(MIXED)

    assert tree.headings()[0].isExpanded()


def test_landing_on_a_heading_leaves_the_reader_where_they_were(
    application,
) -> None:
    """A heading is not a skill, so choosing one reports no change."""
    tree = a_tree(application, MIXED)
    tree.headings()[0].setExpanded(True)
    tree.setCurrentItem(tree.skill_items()[0])
    announced: list[Skill] = []
    tree.skill_selected.connect(announced.append)

    tree.setCurrentItem(tree.headings()[1])

    assert announced == []
    assert tree.selected_skill() is not None


def test_the_selected_skill_survives_the_library_being_read_again(
    application,
) -> None:
    tree = a_tree(application, MIXED)
    for heading in tree.headings():
        heading.setExpanded(True)
    tree.setCurrentItem(tree.skill_items()[1])
    chosen = tree.selected_skill()

    tree.show_catalogue(MIXED)

    assert tree.selected_skill() == chosen


def test_an_empty_library_selects_nothing(application) -> None:
    tree = a_tree(application, SkillCatalogue())

    assert tree.selected_skill() is None
    assert tree.skill_items() == []


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
    tree = a_tree(application, MIXED)
    before = tree.headings()[0].icon(FIRST_COLUMN).pixmap(ARROW_PX, ARROW_PX).toImage()

    tree.wear(LIGHT)
    after = tree.headings()[0].icon(FIRST_COLUMN).pixmap(ARROW_PX, ARROW_PX).toImage()

    assert before != after


def test_clicking_a_heading_opens_and_closes_its_group(application) -> None:
    tree = a_tree(application, MIXED)
    heading = tree.headings()[0]

    tree.itemClicked.emit(heading, FIRST_COLUMN)
    opened = heading.isExpanded()
    tree.itemClicked.emit(heading, FIRST_COLUMN)

    assert opened
    assert not heading.isExpanded()


def test_clicking_a_skill_does_not_toggle_anything(application) -> None:
    tree = a_tree(application, MIXED)
    heading = tree.headings()[0]
    heading.setExpanded(True)
    skill_row = heading.child(0)

    tree.itemClicked.emit(skill_row, FIRST_COLUMN)

    assert heading.isExpanded()


def test_the_arrow_is_big_enough_to_read_as_a_control(application) -> None:
    """It is something you click, so it needs a target rather than a glyph.

    The figure is a stated minimum rather than a measurement: this harness has
    no real fonts, so its text metrics cannot be used to justify one. At the
    twelve pixels it began at, the arrow read as a speck.
    """
    tree = a_tree(application, MIXED)

    assert ARROW_PX >= MINIMUM_TARGET_PX
    assert tree.iconSize().width() == ARROW_PX
