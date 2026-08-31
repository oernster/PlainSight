"""The application's own questions and commands, above the toolkit.

The service is frozen and holds only its injected dependencies. It answers
questions rather than holding the answers, so the user interface asks whether a
control should be enabled instead of working it out for itself.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..domain.catalogue import SkillCatalogue
from ..domain.settings import Appearance, EditorChoice, Settings
from ..domain.skill import Skill
from .defaults import default_editor, effective_skills_root, plugins_root_for
from .ports import (
    EditorLauncher,
    ExternalOpener,
    PathProbe,
    PlatformPaths,
    SettingsStore,
    SkillRepository,
)


@dataclass(frozen=True, slots=True)
class SkillLibraryService:
    """Reads the library, remembers the choices and hands work outwards."""

    repository: SkillRepository
    settings_store: SettingsStore
    launcher: EditorLauncher
    opener: ExternalOpener
    probe: PathProbe
    paths: PlatformPaths

    def current_root(self) -> str:
        """The root that would be read now."""
        return effective_skills_root(self.settings_store.load().skills_root, self.paths)

    def load(self) -> SkillCatalogue:
        """Every skill the current root and the plugins beside it hold."""
        return self._read(self.current_root())

    def choose_root(self, root: str) -> SkillCatalogue:
        """Remember this root and read it."""
        settings = self.settings_store.load().with_root(root)
        self.settings_store.save(settings)
        return self._read(root)

    def _read(self, root: str) -> SkillCatalogue:
        """One catalogue from both places a skill can come from.

        They are combined here rather than in the user interface, so grouping
        stays a property of the library rather than of the widget showing it.
        """
        mine = self.repository.list_skills(root)
        theirs = self.repository.list_plugin_skills(plugins_root_for(root))
        return SkillCatalogue.of((*mine, *theirs))

    def choose_editor(self, editor: EditorChoice) -> None:
        """Remember the editor to launch skills in."""
        self.settings_store.save(self.settings_store.load().with_editor(editor))

    def opened_groups(self) -> tuple[str, ...]:
        """The groups the user has open; none at all until one is opened."""
        return self.settings_store.load().opened_groups

    def remember_opened_groups(self, opened: tuple[str, ...]) -> None:
        """Remember which groups are open, so a run opens as the last one closed."""
        self.settings_store.save(self.settings_store.load().with_opened_groups(opened))

    def appearance(self) -> Appearance:
        """The palette the application should draw with now."""
        return self.settings_store.load().appearance

    def switch_appearance(self) -> Appearance:
        """Remember the other appearance; report which it now is."""
        wanted = self.settings_store.load().appearance.other
        self.settings_store.save(self.settings_store.load().with_appearance(wanted))
        return wanted

    def settings(self) -> Settings:
        """What is remembered right now."""
        return self.settings_store.load()

    def effective_editor(self) -> EditorChoice | None:
        """The editor to use: the one chosen, else the machine's own default."""
        chosen = self.settings_store.load().editor
        return chosen if chosen is not None else default_editor(self.paths, self.probe)

    def can_open_in_editor(self, skill: Skill | None) -> bool:
        """Whether the view in editor control has anything it could do.

        A skill has to be selected, an editor has to have been chosen and that
        editor has to still be where it was when it was chosen; an editor
        uninstalled since is no longer a thing this can act on.
        """
        if skill is None:
            return False
        editor = self.effective_editor()
        if editor is None:
            return False
        return self.probe.exists(editor.path)

    def open_in_editor(self, skill: Skill) -> bool:
        """Open this skill's document in the chosen editor.

        False when there is no usable editor or the desktop declined to start
        it, which the caller reports rather than swallowing.
        """
        editor = self.effective_editor()
        if editor is None:
            return False
        return self.launcher.launch(editor, skill.document_path)

    def open_donation_page(self, address: str) -> bool:
        """Hand the donation address to the desktop; False when it declined."""
        return self.opener.open(address)
