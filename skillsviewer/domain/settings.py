"""What the application remembers between runs: a root plus an editor."""

from __future__ import annotations

from dataclasses import dataclass


class InvalidEditorChoice(ValueError):
    """An editor was chosen in a way that cannot be acted on."""


@dataclass(frozen=True, slots=True)
class EditorChoice:
    """The editor the user picked, with the name to show for it."""

    path: str
    display_name: str

    def __post_init__(self) -> None:
        if not self.path.strip():
            raise InvalidEditorChoice("an editor choice needs a path")
        if not self.display_name.strip():
            raise InvalidEditorChoice("an editor choice needs a display name")


@dataclass(frozen=True, slots=True)
class Settings:
    """Everything the application carries from one run to the next.

    An empty root means the user has never chosen one, so the per-operating-system
    default applies.
    """

    skills_root: str = ""
    editor: EditorChoice | None = None

    def with_root(self, root: str) -> Settings:
        """A copy remembering this root."""
        return Settings(skills_root=root, editor=self.editor)

    def with_editor(self, editor: EditorChoice) -> Settings:
        """A copy remembering this editor."""
        return Settings(skills_root=self.skills_root, editor=editor)
