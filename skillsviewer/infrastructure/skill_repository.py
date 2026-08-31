"""Reads a directory tree and reports the skills in it.

The rules it applies are the ones in the design plan, section 1: a skill is a
directory holding SKILL.md, a loose SKILL.md at the root is a skill of its own,
everything else in a skill's directory is a companion, then hidden and cache
directories are passed over.

A plugins tree is read by the same rules at any depth rather than by a path
template. The measured layout nests a skill four levels down, under a
marketplace and then a plugin. That shape belongs to the tool rather than to
this application; a rule that says "every SKILL.md beneath here" outlives a
layout change, where a template quietly stops finding anything.
"""

from __future__ import annotations

from pathlib import Path

from ..domain.catalogue import SkillCatalogue
from ..domain.origin import SkillOrigin
from ..domain.skill import Skill
from ..domain.skill_document import parse_document

DOCUMENT_NAME = "SKILL.md"
HIDDEN_PREFIX = "."
IGNORED_DIRECTORY_NAMES = frozenset({"__pycache__"})
ROOT_SKILL_FALLBACK_NAME = "SKILL"
PLUGIN_SKILLS_DIRECTORY = "skills"
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

    def list_plugin_skills(self, root: str) -> SkillCatalogue:
        """Every skill held anywhere beneath a plugins tree."""
        base = Path(root)
        if not base.is_dir():
            return SkillCatalogue()
        return SkillCatalogue.of(self._plugin_skills_in(base))

    def _plugin_skills_in(self, base: Path) -> list[Skill]:
        """Every document in the tree, each named for the plugin it came with."""
        found: list[Skill] = []
        for document in sorted(base.rglob(DOCUMENT_NAME)):
            directory = document.parent
            if _is_ignored_anywhere(directory.relative_to(base)):
                continue
            found.append(
                self._read(
                    document,
                    directory,
                    directory.name,
                    _companions(directory, document),
                    origin=SkillOrigin.PLUGIN,
                    source_name=_plugin_name(directory),
                )
            )
        return found

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
        origin: SkillOrigin = SkillOrigin.PERSONAL,
        source_name: str = "",
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
            origin=origin,
            source_name=source_name,
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


def _plugin_name(directory: Path) -> str:
    """The plugin a skill arrived with.

    A plugin gathers its skills in a directory called ``skills``, so the plugin
    is that directory's own parent. Where a document sits somewhere else, the
    directory holding it is the best name there is and is used rather than a
    blank.
    """
    parent = directory.parent
    if parent.name == PLUGIN_SKILLS_DIRECTORY:
        return parent.parent.name
    return parent.name


def _is_ignored_anywhere(relative: Path) -> bool:
    """Whether any step of this path is a directory that is passed over."""
    return any(_is_ignored(part) for part in relative.parts)
