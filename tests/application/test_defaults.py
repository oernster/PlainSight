"""Where the documents live by default; where the plugins beside them live."""

from __future__ import annotations

import os

from plainsight.application.defaults import (
    browse_from,
    chosen_root,
    default_editor,
    documents_root,
    plugins_root_for,
)
from plainsight.domain.settings import EditorChoice

from .fakes import FakePaths, FakeProbe


def test_the_documents_folder_sits_beneath_the_home_directory() -> None:
    home = os.path.join("/home", "oliver")
    documents = os.path.join(home, "Documents")

    root = documents_root(FakePaths(home=home), FakeProbe(present=(documents,)))

    assert root == documents


def test_a_machine_with_no_documents_folder_falls_back_to_the_home_directory() -> None:
    """A chooser sent to a folder that is not there opens somewhere arbitrary."""
    home = os.path.join("/home", "oliver")

    assert documents_root(FakePaths(home=home), FakeProbe()) == home


def test_the_root_to_read_is_whatever_the_user_chose() -> None:
    assert chosen_root("/elsewhere/skills") == "/elsewhere/skills"


def test_nothing_chosen_means_nothing_to_read() -> None:
    """There is no fallback: an unasked walk of a home directory is a rummage."""
    assert chosen_root("   ") == ""


def test_the_chooser_opens_on_the_last_folder_taken() -> None:
    assert (
        browse_from("/elsewhere/skills", FakePaths(), FakeProbe())
        == "/elsewhere/skills"
    )


def test_with_nothing_taken_the_chooser_opens_on_the_documents_folder() -> None:
    """A starting place for a dialog, which reads nothing by being offered."""
    paths = FakePaths(home="/home/oliver")
    probe = FakeProbe(present=(os.path.join("/home/oliver", "Documents"),))

    assert browse_from("   ", paths, probe) == documents_root(paths, probe)


def test_the_plugins_tree_is_found_beside_the_chosen_folder() -> None:
    root = os.path.join("C:", os.sep, "u", ".claude", "skills")

    assert plugins_root_for(root) == os.path.join(
        "C:", os.sep, "u", ".claude", "plugins"
    )


def test_a_trailing_separator_does_not_move_the_plugins_tree() -> None:
    plain = os.path.join("home", ".claude", "skills")

    assert plugins_root_for(plain + os.sep) == plugins_root_for(plain)


def test_an_unrelated_folder_implies_no_plugins_tree_at_all() -> None:
    """Choosing a notes folder must not send this reading its neighbour.

    The rule used to be "the sibling called plugins, whatever you chose", so
    picking `C:\\Work\\Notes` walked `C:\\Work\\plugins`, a directory nobody
    offered. Only a Claude skills folder implies a pair.
    """
    assert plugins_root_for(os.path.join("some", "where")) == ""


def test_a_skills_folder_outside_a_claude_directory_implies_nothing() -> None:
    assert plugins_root_for(os.path.join("some", "where", "skills")) == ""


def test_a_claude_directory_holding_something_else_implies_nothing() -> None:
    assert plugins_root_for(os.path.join("home", ".claude", "notes")) == ""


def test_a_relocated_claude_directory_is_still_recognised() -> None:
    """The rule reads the two directory names, never the home directory."""
    root = os.path.join("D:", os.sep, "moved", ".claude", "skills")

    assert plugins_root_for(root) == os.path.join(
        "D:", os.sep, "moved", ".claude", "plugins"
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
