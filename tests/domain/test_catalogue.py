"""The ordering rule, the lookup by name and the gathering by origin."""

from __future__ import annotations

from skillsviewer.domain.catalogue import SkillCatalogue
from skillsviewer.domain.origin import SkillOrigin
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


def a_skill_from(origin: SkillOrigin, name: str, plugin: str = "") -> Skill:
    return Skill(
        name=name,
        description="",
        directory=f"/d/{name}",
        document_path=f"/d/{name}/SKILL.md",
        body="body",
        origin=origin,
        source_name=plugin,
    )


def test_the_groups_follow_the_order_the_origins_declare() -> None:
    catalogue = SkillCatalogue.of(
        (
            a_skill_from(SkillOrigin.PLUGIN, "a", "hookify"),
            a_skill_from(SkillOrigin.PERSONAL, "z"),
        )
    )

    assert [group.origin for group in catalogue.groups] == [
        SkillOrigin.PERSONAL,
        SkillOrigin.PLUGIN,
    ]


def test_an_origin_that_contributed_nothing_is_not_a_group() -> None:
    catalogue = SkillCatalogue.of((a_skill_from(SkillOrigin.PERSONAL, "only"),))

    assert len(catalogue.groups) == 1
    assert catalogue.groups[0].origin is SkillOrigin.PERSONAL


def test_a_group_counts_and_walks_the_skills_it_holds() -> None:
    catalogue = SkillCatalogue.of(
        (
            a_skill_from(SkillOrigin.PERSONAL, "b"),
            a_skill_from(SkillOrigin.PERSONAL, "a"),
        )
    )

    group = catalogue.groups[0]

    assert len(group) == 2
    assert [skill.name for skill in group] == ["a", "b"]


def test_an_empty_catalogue_has_no_groups() -> None:
    assert SkillCatalogue().groups == ()


def test_each_origin_names_itself_and_knows_where_it_is_shown() -> None:
    assert SkillOrigin.PERSONAL.label == "Your skills"
    assert SkillOrigin.PLUGIN.label == "Plugin skills"
    assert SkillOrigin.PERSONAL.rank < SkillOrigin.PLUGIN.rank
