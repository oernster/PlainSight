"""One skill: the document that defines it, plus the files that travel with it.

Paths are held as plain strings. The domain reads nothing from disk, so it has
no use for a path object's behaviour and no business importing one.
"""

from __future__ import annotations

from dataclasses import dataclass, field


class InvalidSkill(ValueError):
    """A skill was described in a way that cannot be true."""


@dataclass(frozen=True, slots=True)
class Skill:
    """A skill as the viewer knows it.

    ``failure`` carries the reason a document could not be read or parsed. A
    skill with a failure is still a skill and is still listed, because the user
    neither caused it nor can fix it from here; the reason is what gets shown
    in place of the body.
    """

    name: str
    description: str
    directory: str
    document_path: str
    body: str
    companions: tuple[str, ...] = ()
    failure: str = ""
    declared_fields: tuple[tuple[str, str], ...] = field(default=())

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
