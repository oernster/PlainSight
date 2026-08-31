"""What the application remembers; what it refuses to remember."""

from __future__ import annotations

import pytest

from skillsviewer.domain.settings import EditorChoice, InvalidEditorChoice, Settings


def test_settings_start_with_nothing_remembered() -> None:
    settings = Settings()

    assert settings.skills_root == ""
    assert settings.editor is None


def test_remembering_a_root_leaves_the_editor_alone() -> None:
    editor = EditorChoice(path="/usr/bin/vi", display_name="vi")

    settings = Settings(editor=editor).with_root("/skills")

    assert settings.skills_root == "/skills"
    assert settings.editor is editor


def test_remembering_an_editor_leaves_the_root_alone() -> None:
    settings = Settings(skills_root="/skills").with_editor(
        EditorChoice(path="/usr/bin/vi", display_name="vi")
    )

    assert settings.skills_root == "/skills"
    assert settings.editor is not None
    assert settings.editor.display_name == "vi"


def test_an_editor_needs_a_path() -> None:
    with pytest.raises(InvalidEditorChoice):
        EditorChoice(path="  ", display_name="vi")


def test_an_editor_needs_a_display_name() -> None:
    with pytest.raises(InvalidEditorChoice):
        EditorChoice(path="/usr/bin/vi", display_name=" ")
