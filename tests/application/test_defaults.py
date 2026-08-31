"""Where the skills live when the user has not said otherwise."""

from __future__ import annotations

import os

from skillsviewer.application.defaults import default_skills_root, effective_skills_root

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
