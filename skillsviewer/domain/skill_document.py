"""The parsed form of a skill's ``SKILL.md``: its frontmatter and its body.

Splitting one from the other is pure string work over text somebody else read,
so it belongs here rather than in the reader that fetched the text.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

FRONTMATTER_FENCE = "---"
FIELD_SEPARATOR = ":"
QUOTE_CHARACTERS = "\"'"
NAME_FIELD = "name"
DESCRIPTION_FIELD = "description"

_EMPTY_FIELDS: Mapping[str, str] = MappingProxyType({})


@dataclass(frozen=True, slots=True)
class SkillDocument:
    """A skill document split into its declared fields and its prose."""

    frontmatter: Mapping[str, str]
    body: str

    @property
    def name(self) -> str:
        """The declared name; an empty string when the document declares none."""
        return self.frontmatter.get(NAME_FIELD, "")

    @property
    def description(self) -> str:
        """The declared description; an empty string when there is none."""
        return self.frontmatter.get(DESCRIPTION_FIELD, "")


def parse_document(text: str) -> SkillDocument:
    """Split ``text`` into its frontmatter fields and the body beneath them.

    Text with no opening fence is all body, which is the common case for a
    document somebody wrote by hand. An opening fence with no closing one is
    treated the same way, since guessing where the block was meant to end would
    silently swallow prose.
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != FRONTMATTER_FENCE:
        return SkillDocument(frontmatter=_EMPTY_FIELDS, body=text)

    closing = _closing_fence(lines)
    if closing is None:
        return SkillDocument(frontmatter=_EMPTY_FIELDS, body=text)

    fields = _read_fields(lines[1:closing])
    body = "\n".join(lines[closing + 1 :]).lstrip("\n")
    return SkillDocument(frontmatter=MappingProxyType(fields), body=body)


def _closing_fence(lines: list[str]) -> int | None:
    """The index of the fence closing the block opened on the first line."""
    for index in range(1, len(lines)):
        if lines[index].strip() == FRONTMATTER_FENCE:
            return index
    return None


def _read_fields(lines: list[str]) -> dict[str, str]:
    """Read ``key: value`` pairs, ignoring nested and unparseable lines.

    A nested line (one that is indented) belongs to a structure this reader does
    not model, so it is skipped rather than flattened into a misleading pair.
    """
    fields: dict[str, str] = {}
    for line in lines:
        if not line.strip() or line[:1].isspace():
            continue
        key, separator, value = line.partition(FIELD_SEPARATOR)
        if not separator:
            continue
        fields[key.strip()] = _unquote(value.strip())
    return fields


def _unquote(value: str) -> str:
    """Drop one matching pair of surrounding quotes, where there is one."""
    minimum_quoted_length = 2
    quoted = (
        len(value) >= minimum_quoted_length
        and value[0] == value[-1]
        and value[0] in QUOTE_CHARACTERS
    )
    return value[1:-1] if quoted else value
