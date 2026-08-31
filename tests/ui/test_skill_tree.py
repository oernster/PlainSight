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


def test_enter_shuts_a_heading_and_opens_it_again(application) -> None:
    tree = a_tree(application, MIXED)
    heading = tree.headings()[0]
    tree.setCurrentItem(heading)

    press(tree, Qt.Key.Key_Return)
    shut = heading.isExpanded()
    press(tree, Qt.Key.Key_Return)

    assert not shut
    assert heading.isExpanded()


def test_space_toggles_a_heading_too(application) -> None:
    tree = a_tree(application, MIXED)
    heading = tree.headings()[0]
    tree.setCurrentItem(heading)

    press(tree, Qt.Key.Key_Space)

    assert not heading.isExpanded()


def test_a_shut_heading_stays_shut_when_the_library_is_read_again(
    application,
) -> None:
    tree = a_tree(application, MIXED)
    tree.headings()[0].setExpanded(False)

    tree.show_catalogue(MIXED)

    assert not tree.headings()[0].isExpanded()


def test_landing_on_a_heading_leaves_the_reader_where_they_were(
    application,
) -> None:
    """A heading is not a skill, so choosing one reports no change."""
    tree = a_tree(application, MIXED)
    announced: list[Skill] = []
    tree.skill_selected.connect(announced.append)

    tree.setCurrentItem(tree.headings()[1])

    assert announced == []
    assert tree.selected_skill() is not None


def test_the_selected_skill_survives_the_library_being_read_again(
    application,
) -> None:
    tree = a_tree(application, MIXED)
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
