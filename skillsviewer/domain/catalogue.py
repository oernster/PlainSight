"""An ordered collection of skills, with the one ordering rule the app has."""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from dataclasses import dataclass

from .skill import Skill


@dataclass(frozen=True, slots=True)
class SkillCatalogue:
    """The skills found beneath one root, in display order."""

    skills: tuple[Skill, ...] = ()

    @staticmethod
    def of(skills: Iterable[Skill]) -> SkillCatalogue:
        """Build a catalogue, ordered case-insensitively by display name."""
        return SkillCatalogue(tuple(sorted(skills, key=lambda skill: skill.sort_key)))

    def by_name(self, name: str) -> Skill | None:
        """The skill with this display name; None when there is no such skill."""
        for skill in self.skills:
            if skill.name == name:
                return skill
        return None

    @property
    def is_empty(self) -> bool:
        """Whether the root held no skills at all."""
        return not self.skills

    def __len__(self) -> int:
        return len(self.skills)

    def __iter__(self) -> Iterator[Skill]:
        return iter(self.skills)
