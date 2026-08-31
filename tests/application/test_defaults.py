"""Where the skills live; where the plugins beside them live."""

from __future__ import annotations

import os

from skillsviewer.application.defaults import (
    default_editor,
    default_skills_root,
    effective_skills_root,
    plugins_root_for,
)
from skillsviewer.domain.settings import EditorChoice

from .fakes import FakePaths, FakeProbe


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


A_PROGRAMS = os.path.join("C:", os.sep, "Program Files")
ANOTHER = os.path.join("C:", os.sep, "Program Files (x86)")
A_SYSTEM = os.path.join("C:", os.sep, "Windows", "System32")
NOTEPAD_PLUS = os.path.join(A_PROGRAMS, "Notepad++", "notepad++.exe")
NOTEPAD_PLUS_ELSEWHERE = os.path.join(ANOTHER, "Notepad++", "notepad++.exe")
NOTEPAD = os.path.join(A_SYSTEM, "notepad.exe")


def test_notepad_plus_is_preferred_where_it_is_installed() -> None:
    paths = FakePaths(programs=(A_PROGRAMS, ANOTHER), system=A_SYSTEM)
    probe = FakeProbe((NOTEPAD_PLUS, NOTEPAD))

    chosen = default_editor(paths, probe)

    assert chosen == EditorChoice(path=NOTEPAD_PLUS, display_name="Notepad++")


def test_notepad_plus_is_found_in_any_programs_directory_named() -> None:
    paths = FakePaths(programs=(A_PROGRAMS, ANOTHER), system=A_SYSTEM)
    probe = FakeProbe((NOTEPAD_PLUS_ELSEWHERE, NOTEPAD))

    assert default_editor(paths, probe).path == NOTEPAD_PLUS_ELSEWHERE


def test_notepad_is_the_fallback_when_the_better_one_is_absent() -> None:
    paths = FakePaths(programs=(A_PROGRAMS,), system=A_SYSTEM)
    probe = FakeProbe((NOTEPAD,))

    chosen = default_editor(paths, probe)

    assert chosen == EditorChoice(path=NOTEPAD, display_name="Notepad")


def test_a_machine_with_neither_gets_no_default_at_all() -> None:
    paths = FakePaths(programs=(A_PROGRAMS,), system=A_SYSTEM)

    assert default_editor(paths, FakeProbe()) is None


def test_a_machine_that_names_no_system_directory_gets_no_default() -> None:
    """Nothing here is Windows by assumption; elsewhere it simply finds none."""
    paths = FakePaths(programs=(), system="")

    assert default_editor(paths, FakeProbe((NOTEPAD,))) is None
