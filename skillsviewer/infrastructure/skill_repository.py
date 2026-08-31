"""Reads a directory tree and reports the skills in it.

The rules it applies are the ones in the design plan, section 1: a skill is a
directory holding SKILL.md, a loose SKILL.md at the root is a skill of its own,
everything else in a skill's directory is a companion, then hidden and cache
directories are passed over.
"""

from __future__ import annotations

from pathlib import Path

from ..domain.catalogue import SkillCatalogue
from ..domain.skill import Skill
from ..domain.skill_document import parse_document

DOCUMENT_NAME = "SKILL.md"
HIDDEN_PREFIX = "."
IGNORED_DIRECTORY_NAMES = frozenset({"__pycache__"})
ROOT_SKILL_FALLBACK_NAME = "SKILL"
UNREADABLE_TEXT = "This skill's document could not be read as text."
MISSING_TEXT = "This skill's document could not be opened."
EMPTY_TEXT = "This skill's document holds no text beneath its frontmatter."


class FileSystemSkillRepository:
    """Lists the skills held beneath a directory on this machine."""

    def list_skills(self, root: str) -> SkillCatalogue:
        """Every skill beneath ``root``; an empty catalogue when there are none."""
        base = Path(root)
        if not base.is_dir():
            return SkillCatalogue()
        return SkillCatalogue.of(self._skills_in(base))

    def _skills_in(self, base: Path) -> list[Skill]:
        """The loose document, where there is one, then each skill directory."""
        found: list[Skill] = []
        loose = base / DOCUMENT_NAME
        if loose.is_file():
            found.append(self._read(loose, base, ROOT_SKILL_FALLBACK_NAME, ()))
        for entry in sorted(base.iterdir()):
            if not entry.is_dir() or _is_ignored(entry.name):
                continue
            document = entry / DOCUMENT_NAME
            if document.is_file():
                companions = _companions(entry, document)
                found.append(self._read(document, entry, entry.name, companions))
        return found

    def _read(
        self,
        document: Path,
        directory: Path,
        fallback_name: str,
        companions: tuple[str, ...],
    ) -> Skill:
        """Build one skill from its document, reporting a read that failed.

        The loose document at the root of a tree is given no companions: its
        directory is the tree itself, whose other files belong to nobody.
        """
        text, failure = _read_text(document)
        parsed = parse_document(text)
        if not failure and not parsed.body.strip():
            failure = EMPTY_TEXT
        return Skill(
            name=parsed.name.strip() or fallback_name,
            description=parsed.description,
            directory=str(directory),
            document_path=str(document),
            body=parsed.body,
            companions=companions,
            failure=failure,
            declared_fields=tuple(parsed.frontmatter.items()),
        )


def _read_text(document: Path) -> tuple[str, str]:
    """The document's text with no failure; else empty text with a reason."""
    try:
        return document.read_text(encoding="utf-8"), ""
    except UnicodeDecodeError:
        return "", UNREADABLE_TEXT
    except OSError:
        return "", MISSING_TEXT


def _companions(directory: Path, document: Path) -> tuple[str, ...]:
    """The files beside the document that travel with the skill."""
    return tuple(
        str(entry)
        for entry in sorted(directory.iterdir())
        if entry.is_file() and entry != document
    )


def _is_ignored(name: str) -> bool:
    """Whether a directory of this name is passed over rather than scanned."""
    return name.startswith(HIDDEN_PREFIX) or name in IGNORED_DIRECTORY_NAMES
