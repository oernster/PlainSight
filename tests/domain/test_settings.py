"""What the application remembers; what it refuses to remember."""

from __future__ import annotations

import pytest

from skillsviewer.domain.settings import (
    DEFAULT_APPEARANCE,
    DEFAULT_FONT_SIZE,
    Appearance,
    EditorChoice,
    FontSize,
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


def test_the_default_text_size_is_the_middle_one() -> None:
    assert DEFAULT_FONT_SIZE is FontSize.MEDIUM
    assert Settings().font_size is FontSize.MEDIUM


def test_the_sizes_step_upward_then_wrap() -> None:
    assert FontSize.MEDIUM.next_in_cycle is FontSize.LARGE
    assert FontSize.LARGE.next_in_cycle is FontSize.EXTRA_LARGE
    assert FontSize.EXTRA_LARGE.next_in_cycle is FontSize.MEDIUM


def test_walking_the_cycle_returns_to_where_it_started() -> None:
    size = FontSize.MEDIUM
    for _step in FontSize:
        size = size.next_in_cycle

    assert size is FontSize.MEDIUM


@pytest.mark.parametrize(
    ("recorded", "expected"),
    [
        ("medium", FontSize.MEDIUM),
        ("large", FontSize.LARGE),
        ("extra_large", FontSize.EXTRA_LARGE),
        ("enormous", DEFAULT_FONT_SIZE),
        ("", DEFAULT_FONT_SIZE),
    ],
)
def test_a_recorded_size_reads_back_or_falls_to_the_default(
    recorded: str, expected: FontSize
) -> None:
    assert FontSize.of(recorded) is expected


def test_a_text_size_replaces_only_itself() -> None:
    settings = Settings(skills_root="/skills", opened_groups=("prose",))

    changed = settings.with_font_size(FontSize.LARGE)

    assert changed.font_size is FontSize.LARGE
    assert changed.skills_root == "/skills"
    assert changed.opened_groups == ("prose",)
    assert settings.font_size is FontSize.MEDIUM


def test_every_other_copy_carries_the_text_size_over() -> None:
    settings = Settings().with_font_size(FontSize.EXTRA_LARGE)

    assert settings.with_root("/skills").font_size is FontSize.EXTRA_LARGE
    assert settings.with_appearance(Appearance.LIGHT).font_size is FontSize.EXTRA_LARGE
