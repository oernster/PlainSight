"""Where the skills live; where the plugins beside them live."""

from __future__ import annotations

import os

from skillsviewer.application.defaults import (
    default_skills_root,
    effective_skills_root,
    plugins_root_for,
)

from .fakes import FakePaths


def test_the_default_root_sits_beneath_the_home_directory() -> None:
    root = default_skills_root(FakePaths(home=os.path.join("/home", "oliver")))

    assert root == os.path.join("/home", "oliver", ".claude", "skills")


def test_a_remembered_root_is_used_in_place_of_the_default() -> None:
    root = effective_skills_root("/elsewhere/skills", FakePaths())

    assert root == "/elsewhere/skills"


def test_a_blank_remembered_root_falls_back_to_the_default() -> None:
    root = effective_skills_root("   ", FakePaths(home="/home/oliver"))

    assert root == default_skills_root(FakePaths(home="/home/oliver"))


def test_the_plugins_tree_is_found_beside_the_skills_folder() -> None:
    root = os.path.join("C:", os.sep, "u", ".claude", "skills")

    assert plugins_root_for(root) == os.path.join(
        "C:", os.sep, "u", ".claude", "plugins"
    )


def test_a_trailing_separator_does_not_move_the_plugins_tree() -> None:
    plain = os.path.join("home", ".claude", "skills")

    assert plugins_root_for(plain + os.sep) == plugins_root_for(plain)


def test_an_unrelated_folder_points_at_a_plugins_tree_that_is_not_there() -> None:
    assert plugins_root_for(os.path.join("some", "where")) == os.path.join(
        "some", "plugins"
    )
