"""Reading a real tree, against the rules of design plan section 1."""

from __future__ import annotations

from pathlib import Path

from skillsviewer.domain.origin import SkillOrigin
from skillsviewer.infrastructure.skill_repository import (
    EMPTY_TEXT,
    UNREADABLE_TEXT,
    FileSystemSkillRepository,
)

A_DOCUMENT = "---\nname: prose\ndescription: writing\n---\n\n# Prose\n\nBody.\n"


def write_skill(root: Path, name: str, text: str = A_DOCUMENT) -> Path:
    directory = root / name
    directory.mkdir(parents=True)
    (directory / "SKILL.md").write_text(text, encoding="utf-8")
    return directory


def test_a_directory_holding_a_document_is_a_skill(tmp_path: Path) -> None:
    write_skill(tmp_path, "prose")

    catalogue = FileSystemSkillRepository().list_skills(str(tmp_path))

    assert [skill.name for skill in catalogue] == ["prose"]


def test_a_directory_with_no_document_is_not_a_skill(tmp_path: Path) -> None:
    (tmp_path / "references").mkdir()
    (tmp_path / "references" / "notes.md").write_text("notes", encoding="utf-8")

    catalogue = FileSystemSkillRepository().list_skills(str(tmp_path))

    assert catalogue.is_empty


def test_a_loose_document_at_the_root_is_a_skill(tmp_path: Path) -> None:
    (tmp_path / "SKILL.md").write_text(A_DOCUMENT, encoding="utf-8")

    catalogue = FileSystemSkillRepository().list_skills(str(tmp_path))

    assert [skill.name for skill in catalogue] == ["prose"]
    assert catalogue.skills[0].companions == ()


def test_a_document_declaring_no_name_falls_back_to_its_directory(
    tmp_path: Path,
) -> None:
    write_skill(tmp_path, "keeb", text="# Keeb\n\nBody.\n")

    catalogue = FileSystemSkillRepository().list_skills(str(tmp_path))

    assert [skill.name for skill in catalogue] == ["keeb"]


def test_files_beside_the_document_are_companions(tmp_path: Path) -> None:
    directory = write_skill(tmp_path, "dev")
    (directory / "packaging.md").write_text("recipes", encoding="utf-8")

    catalogue = FileSystemSkillRepository().list_skills(str(tmp_path))

    assert catalogue.skills[0].companions == (str(directory / "packaging.md"),)


def test_hidden_and_cache_directories_are_passed_over(tmp_path: Path) -> None:
    write_skill(tmp_path, ".ruff_cache", text="# Cache\n\nText.\n")
    write_skill(tmp_path, "__pycache__", text="# Cache\n\nText.\n")
    write_skill(tmp_path, "prose")

    catalogue = FileSystemSkillRepository().list_skills(str(tmp_path))

    assert [skill.name for skill in catalogue] == ["prose"]


def test_a_document_that_is_not_text_is_still_listed(tmp_path: Path) -> None:
    directory = tmp_path / "broken"
    directory.mkdir()
    (directory / "SKILL.md").write_bytes(b"\xff\xfe\x00binary")

    catalogue = FileSystemSkillRepository().list_skills(str(tmp_path))

    assert catalogue.skills[0].failure == UNREADABLE_TEXT
    assert not catalogue.skills[0].is_readable


def test_a_document_with_no_prose_reports_that_rather_than_vanishing(
    tmp_path: Path,
) -> None:
    write_skill(tmp_path, "hollow", text="---\nname: hollow\n---\n")

    catalogue = FileSystemSkillRepository().list_skills(str(tmp_path))

    assert catalogue.skills[0].failure == EMPTY_TEXT


def test_a_root_that_is_not_there_gives_an_empty_catalogue(tmp_path: Path) -> None:
    catalogue = FileSystemSkillRepository().list_skills(str(tmp_path / "absent"))

    assert catalogue.is_empty


def test_skills_come_back_in_display_order(tmp_path: Path) -> None:
    unnamed = "# Body\n\nText.\n"
    write_skill(tmp_path, "prose", text=unnamed)
    write_skill(tmp_path, "Dev", text=unnamed)
    write_skill(tmp_path, "da", text=unnamed)

    catalogue = FileSystemSkillRepository().list_skills(str(tmp_path))

    assert [skill.name for skill in catalogue] == ["da", "Dev", "prose"]


def a_plugin_skill(root: Path, plugin: str, skill: str) -> Path:
    """The layout measured on a real machine: plugin, then skills, then one."""
    directory = (
        root / "marketplaces" / "official" / "plugins" / plugin / "skills" / skill
    )
    directory.mkdir(parents=True)
    (directory / "SKILL.md").write_text(
        f"---\nname: {skill}\ndescription: d\n---\n\nBody.\n", encoding="utf-8"
    )
    return directory


def test_a_plugin_skill_is_found_however_deep_it_sits(tmp_path: Path) -> None:
    a_plugin_skill(tmp_path, "hookify", "hookify")

    catalogue = FileSystemSkillRepository().list_plugin_skills(str(tmp_path))

    assert [skill.name for skill in catalogue] == ["hookify"]
    assert catalogue.skills[0].origin is SkillOrigin.PLUGIN


def test_a_plugin_skill_is_named_for_the_plugin_it_came_with(tmp_path: Path) -> None:
    a_plugin_skill(tmp_path, "mcp-server-dev", "build-mcp-server")

    catalogue = FileSystemSkillRepository().list_plugin_skills(str(tmp_path))

    assert catalogue.skills[0].source_name == "mcp-server-dev"


def test_a_document_outside_a_skills_directory_takes_its_own_parent(
    tmp_path: Path,
) -> None:
    directory = tmp_path / "loose" / "somewhere"
    directory.mkdir(parents=True)
    (directory / "SKILL.md").write_text(
        "---\nname: n\n---\n\nBody.\n", encoding="utf-8"
    )

    catalogue = FileSystemSkillRepository().list_plugin_skills(str(tmp_path))

    assert catalogue.skills[0].source_name == "loose"


def test_a_hidden_or_cache_directory_is_passed_over_at_any_depth(
    tmp_path: Path,
) -> None:
    for parent in (".git", "__pycache__"):
        directory = tmp_path / parent / "plugin" / "skills" / "hidden"
        directory.mkdir(parents=True)
        (directory / "SKILL.md").write_text(
            "---\nname: hidden\n---\n\nBody.\n", encoding="utf-8"
        )

    catalogue = FileSystemSkillRepository().list_plugin_skills(str(tmp_path))

    assert catalogue.is_empty


def test_a_plugins_tree_that_is_not_there_holds_nothing(tmp_path: Path) -> None:
    catalogue = FileSystemSkillRepository().list_plugin_skills(str(tmp_path / "absent"))

    assert catalogue.is_empty


def test_a_skill_from_the_skills_folder_names_no_plugin(tmp_path: Path) -> None:
    directory = tmp_path / "prose"
    directory.mkdir()
    (directory / "SKILL.md").write_text(
        "---\nname: prose\n---\n\nBody.\n", encoding="utf-8"
    )

    catalogue = FileSystemSkillRepository().list_skills(str(tmp_path))

    assert catalogue.skills[0].source_name == ""
    assert catalogue.skills[0].origin is SkillOrigin.PERSONAL
