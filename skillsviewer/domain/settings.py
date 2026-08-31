"""What the application remembers between runs: a root, an editor, a look."""

from __future__ import annotations

import enum
from dataclasses import dataclass


class Appearance(enum.Enum):
    """Which of the two palettes the application draws with."""

    DARK = "dark"
    LIGHT = "light"

    @property
    def other(self) -> Appearance:
        """The one a toggle would move to, which is what the toggle shows."""
        return Appearance.LIGHT if self is Appearance.DARK else Appearance.DARK

    @staticmethod
    def of(value: str) -> Appearance:
        """The appearance this recorded value names; dark when it names none."""
        for appearance in Appearance:
            if appearance.value == value:
                return appearance
        return DEFAULT_APPEARANCE


DEFAULT_APPEARANCE = Appearance.DARK


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
    appearance: Appearance = DEFAULT_APPEARANCE

    def with_root(self, root: str) -> Settings:
        """A copy remembering this root."""
        return Settings(
            skills_root=root, editor=self.editor, appearance=self.appearance
        )

    def with_editor(self, editor: EditorChoice) -> Settings:
        """A copy remembering this editor."""
        return Settings(
            skills_root=self.skills_root, editor=editor, appearance=self.appearance
        )

    def with_appearance(self, appearance: Appearance) -> Settings:
        """A copy remembering this appearance."""
        return Settings(
            skills_root=self.skills_root, editor=self.editor, appearance=appearance
        )
