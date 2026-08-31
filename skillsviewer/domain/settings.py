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


class FontSize(enum.Enum):
    """How large the application draws its text.

    Three sizes rather than a continuous scale: the control is one button that
    steps through them, so the set has to be small enough to walk in a moment.
    """

    MEDIUM = "medium"
    LARGE = "large"
    EXTRA_LARGE = "extra_large"

    @property
    def next_in_cycle(self) -> FontSize:
        """The size the button would move to, which is what the button shows.

        The cycle wraps, so the largest steps back to the smallest rather than
        stopping and leaving a control that does nothing.
        """
        order = tuple(FontSize)
        return order[(order.index(self) + 1) % len(order)]

    @staticmethod
    def of(value: str) -> FontSize:
        """The size this recorded value names; the default when it names none."""
        for size in FontSize:
            if size.value == value:
                return size
        return DEFAULT_FONT_SIZE


DEFAULT_FONT_SIZE = FontSize.MEDIUM


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
    default applies. ``opened_groups`` names the groups the user has opened, so
    the empty tuple a fresh install carries is every group shut, which is how it
    opens by design rather than by accident. ``skipped_update_version`` holds the
    exact release tag the user asked not to be told about again; empty means
    every release is worth mentioning.
    """

    skills_root: str = ""
    editor: EditorChoice | None = None
    appearance: Appearance = DEFAULT_APPEARANCE
    font_size: FontSize = DEFAULT_FONT_SIZE
    opened_groups: tuple[str, ...] = ()
    skipped_update_version: str = ""

    def with_root(self, root: str) -> Settings:
        """A copy remembering this root."""
        return self._but(skills_root=root)

    def with_editor(self, editor: EditorChoice) -> Settings:
        """A copy remembering this editor."""
        return self._but(editor=editor)

    def with_appearance(self, appearance: Appearance) -> Settings:
        """A copy remembering this appearance."""
        return self._but(appearance=appearance)

    def with_font_size(self, size: FontSize) -> Settings:
        """A copy remembering this text size."""
        return self._but(font_size=size)

    def with_opened_groups(self, opened: tuple[str, ...]) -> Settings:
        """A copy remembering which groups the user has open."""
        return self._but(opened_groups=opened)

    def with_skipped_update_version(self, tag: str) -> Settings:
        """A copy that will not mention this release again."""
        return self._but(skipped_update_version=tag)

    def _but(self, **changed: object) -> Settings:
        """A copy with these fields replaced and every other one carried over."""
        fields = {
            "skills_root": self.skills_root,
            "editor": self.editor,
            "appearance": self.appearance,
            "font_size": self.font_size,
            "opened_groups": self.opened_groups,
            "skipped_update_version": self.skipped_update_version,
        }
        fields.update(changed)
        return Settings(**fields)  # type: ignore[arg-type]
