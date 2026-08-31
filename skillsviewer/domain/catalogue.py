"""An ordered collection of skills, with the one ordering rule the app has."""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from dataclasses import dataclass

from .origin import SkillOrigin
from .skill import Skill


@dataclass(frozen=True, slots=True)
class SkillGroup:
    """One origin and the skills that came from it, in display order."""

    origin: SkillOrigin
    skills: tuple[Skill, ...]

    def __len__(self) -> int:
        return len(self.skills)

    def __iter__(self) -> Iterator[Skill]:
        return iter(self.skills)


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
    def groups(self) -> tuple[SkillGroup, ...]:
        """The skills gathered by origin, in the order the origins declare.

        An origin that contributed nothing is left out rather than shown as an
        empty heading, so a machine with no plugins sees one list and no
        grouping it did not ask for.
        """
        return tuple(
            SkillGroup(origin, gathered)
            for origin in sorted(SkillOrigin, key=lambda one: one.rank)
            if (gathered := tuple(s for s in self.skills if s.origin is origin))
        )

    @property
    def is_empty(self) -> bool:
        """Whether the root held no skills at all."""
        return not self.skills

    def __len__(self) -> int:
        return len(self.skills)

    def __iter__(self) -> Iterator[Skill]:
        return iter(self.skills)
