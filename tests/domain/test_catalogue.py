"""The one ordering rule the application has, plus lookup by name."""

from __future__ import annotations

from skillsviewer.domain.catalogue import SkillCatalogue
from skillsviewer.domain.skill import Skill


def a_skill(name: str) -> Skill:
    return Skill(
        name=name,
        description="",
        directory=f"/skills/{name}",
        document_path=f"/skills/{name}/SKILL.md",
        body="body",
    )


def test_skills_are_ordered_case_insensitively_by_name() -> None:
    catalogue = SkillCatalogue.of([a_skill("prose"), a_skill("Dev"), a_skill("da")])

    assert [skill.name for skill in catalogue] == ["da", "Dev", "prose"]


def test_a_skill_can_be_found_by_its_name() -> None:
    catalogue = SkillCatalogue.of([a_skill("prose"), a_skill("dev")])

    found = catalogue.by_name("dev")

    assert found is not None
    assert found.name == "dev"


def test_a_name_that_is_not_there_finds_nothing() -> None:
    catalogue = SkillCatalogue.of([a_skill("prose")])

    assert catalogue.by_name("absent") is None


def test_an_empty_catalogue_says_so_and_has_no_length() -> None:
    catalogue = SkillCatalogue()

    assert catalogue.is_empty
    assert len(catalogue) == 0


def test_a_populated_catalogue_is_not_empty() -> None:
    catalogue = SkillCatalogue.of([a_skill("prose")])

    assert not catalogue.is_empty
    assert len(catalogue) == 1
