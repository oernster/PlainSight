"""What a skill will and will not accept as a description of itself."""

from __future__ import annotations

import pytest

from skillsviewer.domain.skill import HEADER_FIELD_LIMIT, InvalidSkill, Skill


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


def test_the_two_fields_the_header_shows_outright_are_not_repeated() -> None:
    skill = a_skill(
        declared_fields=(("name", "prose"), ("description", "d"), ("source", "s"))
    )

    assert skill.header_fields == (("source", "s"),)
    assert skill.long_fields == ()


def test_a_field_at_the_limit_stays_in_the_header() -> None:
    value = "x" * HEADER_FIELD_LIMIT

    skill = a_skill(declared_fields=(("note", value),))

    assert skill.header_fields == (("note", value),)
    assert skill.long_fields == ()


def test_a_field_past_the_limit_leaves_the_header() -> None:
    value = "x" * (HEADER_FIELD_LIMIT + 1)

    skill = a_skill(declared_fields=(("revision_note", value),))

    assert skill.header_fields == ()
    assert skill.long_fields == (("revision_note", value),)


def test_short_and_long_fields_keep_their_declared_order() -> None:
    wall = "x" * (HEADER_FIELD_LIMIT + 1)
    skill = a_skill(
        declared_fields=(("a", wall), ("b", "short"), ("c", wall), ("d", "short"))
    )

    assert skill.header_fields == (("b", "short"), ("d", "short"))
    assert skill.long_fields == (("a", wall), ("c", wall))
