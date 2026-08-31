"""What a skill will and will not accept as a description of itself."""

from __future__ import annotations

import pytest

from skillsviewer.domain.skill import InvalidSkill, Skill


def a_skill(**overrides: object) -> Skill:
    fields: dict[str, object] = {
        "name": "prose",
        "description": "Write it correctly first time",
        "directory": "/skills/prose",
        "document_path": "/skills/prose/SKILL.md",
        "body": "# Prose",
    }
    fields.update(overrides)
    return Skill(**fields)  # type: ignore[arg-type]


def test_a_readable_skill_reports_itself_readable() -> None:
    assert a_skill().is_readable


def test_a_skill_carrying_a_failure_is_not_readable() -> None:
    skill = a_skill(body="", failure="could not be read")

    assert not skill.is_readable


def test_the_sort_key_ignores_case() -> None:
    assert a_skill(name="Prose").sort_key == "prose"


def test_a_skill_needs_a_name() -> None:
    with pytest.raises(InvalidSkill):
        a_skill(name="   ")


def test_a_skill_needs_the_path_of_its_document() -> None:
    with pytest.raises(InvalidSkill):
        a_skill(document_path=" ")


def test_a_skill_needs_a_body_or_a_reason_there_is_none() -> None:
    with pytest.raises(InvalidSkill):
        a_skill(body="  ", failure="")


def test_companions_default_to_none_at_all() -> None:
    assert a_skill().companions == ()
    assert a_skill().declared_fields == ()
