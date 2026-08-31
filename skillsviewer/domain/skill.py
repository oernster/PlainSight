"""One skill: the document that defines it, plus the files that travel with it.

Paths are held as plain strings. The domain reads nothing from disk, so it has
no use for a path object's behaviour and no business importing one.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .origin import SkillOrigin

HEADER_FIELD_CHARS_PER_LINE = 100
HEADER_FIELD_MAX_LINES = 3
HEADER_FIELD_LIMIT = HEADER_FIELD_CHARS_PER_LINE * HEADER_FIELD_MAX_LINES
SHOWN_ALREADY = frozenset({"name", "description"})


class InvalidSkill(ValueError):
    """A skill was described in a way that cannot be true."""


@dataclass(frozen=True, slots=True)
class Skill:
    """A skill as the viewer knows it.

    ``failure`` carries the reason a document could not be read or parsed. A
    skill with a failure is still a skill and is still listed, because the user
    neither caused it nor can fix it from here; the reason is what gets shown
    in place of the body.

    ``source_name`` names the plugin a skill arrived with; it is empty for a
    skill from the skills folder, which arrived with nothing but itself.
    """

    name: str
    description: str
    directory: str
    document_path: str
    body: str
    companions: tuple[str, ...] = ()
    failure: str = ""
    declared_fields: tuple[tuple[str, str], ...] = field(default=())
    origin: SkillOrigin = SkillOrigin.PERSONAL
    source_name: str = ""

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise InvalidSkill("a skill needs a name")
        if not self.document_path.strip():
            raise InvalidSkill("a skill needs the path of its document")
        if not self.body.strip() and not self.failure.strip():
            raise InvalidSkill("a skill needs either a body or a failure to report")

    @property
    def is_readable(self) -> bool:
        """Whether the document was read and parsed without trouble."""
        return not self.failure

    @property
    def sort_key(self) -> str:
        """The key the catalogue orders by: the display name, case folded."""
        return self.name.casefold()

    @property
    def header_fields(self) -> tuple[tuple[str, str], ...]:
        """Declared fields short enough to read as a header row."""
        return tuple(
            pair for pair in self._extra_fields if len(pair[1]) <= HEADER_FIELD_LIMIT
        )

    @property
    def long_fields(self) -> tuple[tuple[str, str], ...]:
        """Declared fields too long for a header row.

        A frontmatter value has no length limit and the longest in the library
        this was measured against runs to eleven thousand characters on one
        line. Shown among the header rows it buries the skill the reader
        opened, so it is separated out here and given a section of its own.
        """
        return tuple(
            pair for pair in self._extra_fields if len(pair[1]) > HEADER_FIELD_LIMIT
        )

    @property
    def _extra_fields(self) -> tuple[tuple[str, str], ...]:
        """Declared fields beyond the two the header already shows outright."""
        return tuple(
            (key, value)
            for key, value in self.declared_fields
            if key not in SHOWN_ALREADY
        )
