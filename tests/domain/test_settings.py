"""What the application remembers; what it refuses to remember."""

from __future__ import annotations

import pytest

from skillsviewer.domain.settings import (
    DEFAULT_APPEARANCE,
    Appearance,
    EditorChoice,
    InvalidEditorChoice,
    Settings,
)


def test_settings_start_with_nothing_remembered() -> None:
    settings = Settings()

    assert settings.skills_root == ""
    assert settings.editor is None
    assert settings.appearance is DEFAULT_APPEARANCE


def test_the_toggle_moves_to_the_other_appearance() -> None:
    assert Appearance.DARK.other is Appearance.LIGHT
    assert Appearance.LIGHT.other is Appearance.DARK


def test_a_recorded_appearance_is_read_back() -> None:
    assert Appearance.of("light") is Appearance.LIGHT
    assert Appearance.of("dark") is Appearance.DARK


def test_an_appearance_nobody_recorded_falls_back_to_the_default() -> None:
    assert Appearance.of("") is DEFAULT_APPEARANCE
    assert Appearance.of("chartreuse") is DEFAULT_APPEARANCE


def test_remembering_an_appearance_leaves_the_rest_alone() -> None:
    editor = EditorChoice(path="/usr/bin/vi", display_name="vi")

    settings = Settings(skills_root="/skills", editor=editor).with_appearance(
        Appearance.LIGHT
    )

    assert settings.appearance is Appearance.LIGHT
    assert settings.skills_root == "/skills"
    assert settings.editor is editor


def test_remembering_a_root_leaves_the_editor_and_appearance_alone() -> None:
    editor = EditorChoice(path="/usr/bin/vi", display_name="vi")

    settings = Settings(editor=editor, appearance=Appearance.LIGHT).with_root("/skills")

    assert settings.skills_root == "/skills"
    assert settings.editor is editor
    assert settings.appearance is Appearance.LIGHT


def test_remembering_an_editor_leaves_the_root_and_appearance_alone() -> None:
    settings = Settings(skills_root="/skills", appearance=Appearance.LIGHT).with_editor(
        EditorChoice(path="/usr/bin/vi", display_name="vi")
    )

    assert settings.skills_root == "/skills"
    assert settings.editor is not None
    assert settings.editor.display_name == "vi"
    assert settings.appearance is Appearance.LIGHT


def test_an_editor_needs_a_path() -> None:
    with pytest.raises(InvalidEditorChoice):
        EditorChoice(path="  ", display_name="vi")


def test_an_editor_needs_a_display_name() -> None:
    with pytest.raises(InvalidEditorChoice):
        EditorChoice(path="/usr/bin/vi", display_name=" ")


def test_nothing_is_skipped_by_default() -> None:
    assert Settings().skipped_update_version == ""


def test_a_skipped_release_replaces_only_itself() -> None:
    settings = Settings(skills_root="/skills", opened_groups=("prose",))

    changed = settings.with_skipped_update_version("0.2.0")

    assert changed.skipped_update_version == "0.2.0"
    assert changed.skills_root == "/skills"
    assert changed.opened_groups == ("prose",)
    assert settings.skipped_update_version == ""


def test_every_other_copy_carries_the_skipped_release_over() -> None:
    settings = Settings().with_skipped_update_version("0.2.0")

    assert settings.with_root("/skills").skipped_update_version == "0.2.0"
    assert settings.with_opened_groups(()).skipped_update_version == "0.2.0"
