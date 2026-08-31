"""The questions the user interface asks, answered by the service."""

from __future__ import annotations

import os

from skillsviewer.application.defaults import default_skills_root
from skillsviewer.application.services import SkillLibraryService
from skillsviewer.domain.catalogue import SkillCatalogue
from skillsviewer.domain.origin import SkillOrigin
from skillsviewer.domain.settings import Appearance, EditorChoice, Settings
from skillsviewer.domain.skill import Skill

from .fakes import (
    FakeLauncher,
    FakeOpener,
    FakePaths,
    FakeProbe,
    FakeRepository,
    FakeSettingsStore,
    a_skill,
)

AN_EDITOR = EditorChoice(path="/usr/bin/vi", display_name="vi")
A_DONATION_ADDRESS = "https://example.invalid/donate"


def a_service(
    repository: FakeRepository | None = None,
    store: FakeSettingsStore | None = None,
    launcher: FakeLauncher | None = None,
    opener: FakeOpener | None = None,
    probe: FakeProbe | None = None,
    paths: FakePaths | None = None,
) -> SkillLibraryService:
    return SkillLibraryService(
        repository=repository if repository is not None else FakeRepository(),
        settings_store=store if store is not None else FakeSettingsStore(),
        launcher=launcher if launcher is not None else FakeLauncher(),
        opener=opener if opener is not None else FakeOpener(),
        probe=probe if probe is not None else FakeProbe(),
        paths=paths if paths is not None else FakePaths(),
    )


def test_the_current_root_is_the_default_when_nothing_was_remembered() -> None:
    paths = FakePaths(home="/home/oliver")

    service = a_service(paths=paths)

    assert service.current_root() == default_skills_root(paths)


def test_loading_reads_the_current_root() -> None:
    repository = FakeRepository()
    store = FakeSettingsStore(Settings(skills_root="/elsewhere"))

    a_service(repository=repository, store=store).load()

    assert repository.roots_read == ["/elsewhere"]


def test_choosing_a_root_remembers_it_and_reads_it() -> None:
    repository = FakeRepository(SkillCatalogue.of([a_skill()]))
    store = FakeSettingsStore()

    catalogue = a_service(repository=repository, store=store).choose_root("/chosen")

    assert store.settings.skills_root == "/chosen"
    assert repository.roots_read == ["/chosen"]
    assert len(catalogue) == 1


def test_choosing_an_editor_remembers_it() -> None:
    store = FakeSettingsStore()

    a_service(store=store).choose_editor(AN_EDITOR)

    assert store.settings.editor == AN_EDITOR


def test_the_appearance_starts_dark() -> None:
    assert a_service().appearance() is Appearance.DARK


def test_switching_remembers_the_other_appearance_and_reports_it() -> None:
    store = FakeSettingsStore()
    service = a_service(store=store)

    assert service.switch_appearance() is Appearance.LIGHT
    assert store.settings.appearance is Appearance.LIGHT
    assert service.appearance() is Appearance.LIGHT


def test_switching_twice_returns_to_where_it_started() -> None:
    service = a_service(store=FakeSettingsStore())

    service.switch_appearance()

    assert service.switch_appearance() is Appearance.DARK


def test_the_settings_can_be_read_back() -> None:
    store = FakeSettingsStore(Settings(skills_root="/elsewhere"))

    assert a_service(store=store).settings().skills_root == "/elsewhere"


def test_no_skill_selected_means_the_editor_control_can_do_nothing() -> None:
    store = FakeSettingsStore(Settings(editor=AN_EDITOR))
    probe = FakeProbe(present=(AN_EDITOR.path,))

    assert not a_service(store=store, probe=probe).can_open_in_editor(None)


def test_no_editor_chosen_means_the_editor_control_can_do_nothing() -> None:
    assert not a_service().can_open_in_editor(a_skill())


def test_an_editor_that_has_gone_means_the_control_can_do_nothing() -> None:
    store = FakeSettingsStore(Settings(editor=AN_EDITOR))

    service = a_service(store=store, probe=FakeProbe(present=()))

    assert not service.can_open_in_editor(a_skill())


def test_a_skill_plus_an_editor_that_is_there_enables_the_control() -> None:
    store = FakeSettingsStore(Settings(editor=AN_EDITOR))
    probe = FakeProbe(present=(AN_EDITOR.path,))

    assert a_service(store=store, probe=probe).can_open_in_editor(a_skill())


def test_opening_hands_the_document_to_the_chosen_editor() -> None:
    store = FakeSettingsStore(Settings(editor=AN_EDITOR))
    launcher = FakeLauncher()
    skill = a_skill()

    assert a_service(store=store, launcher=launcher).open_in_editor(skill)
    assert launcher.launched == [(AN_EDITOR, skill.document_path)]


def test_opening_without_an_editor_reports_that_it_did_nothing() -> None:
    launcher = FakeLauncher()

    assert not a_service(launcher=launcher).open_in_editor(a_skill())
    assert launcher.launched == []


def test_a_desktop_that_declines_the_editor_is_reported() -> None:
    store = FakeSettingsStore(Settings(editor=AN_EDITOR))

    service = a_service(store=store, launcher=FakeLauncher(accepts=False))

    assert not service.open_in_editor(a_skill())


def test_the_donation_address_is_handed_over_untouched() -> None:
    opener = FakeOpener()

    assert a_service(opener=opener).open_donation_page(A_DONATION_ADDRESS)
    assert opener.opened == [A_DONATION_ADDRESS]


def test_a_desktop_that_declines_the_donation_page_is_reported() -> None:
    service = a_service(opener=FakeOpener(accepts=False))

    assert not service.open_donation_page(A_DONATION_ADDRESS)


def test_loading_reads_the_plugins_tree_beside_the_root_too() -> None:
    repository = FakeRepository()
    store = FakeSettingsStore(
        Settings(skills_root=os.path.join("home", ".claude", "skills"))
    )

    a_service(repository=repository, store=store).load()

    assert repository.plugin_roots_read == [os.path.join("home", ".claude", "plugins")]


def test_both_places_arrive_as_one_catalogue_gathered_by_origin() -> None:
    mine = Skill(
        name="prose",
        description="",
        directory="/d",
        document_path="/d/SKILL.md",
        body="body",
    )
    theirs = Skill(
        name="hookify",
        description="",
        directory="/p",
        document_path="/p/SKILL.md",
        body="body",
        origin=SkillOrigin.PLUGIN,
        source_name="hookify",
    )
    repository = FakeRepository(SkillCatalogue.of([mine]), SkillCatalogue.of([theirs]))

    catalogue = a_service(repository=repository).load()

    assert len(catalogue) == 2
    assert [group.origin for group in catalogue.groups] == [
        SkillOrigin.PERSONAL,
        SkillOrigin.PLUGIN,
    ]


def test_choosing_a_root_reads_the_plugins_beside_that_one() -> None:
    repository = FakeRepository()
    chosen = os.path.join("other", ".claude", "skills")

    a_service(repository=repository).choose_root(chosen)

    assert repository.plugin_roots_read == [os.path.join("other", ".claude", "plugins")]


def test_a_remembered_editor_beats_the_machine_default() -> None:
    chosen = EditorChoice(path="/usr/bin/vi", display_name="vi")
    store = FakeSettingsStore(Settings(editor=chosen))
    paths = FakePaths(programs=("/programs",), system="/system")

    service = a_service(
        store=store, paths=paths, probe=FakeProbe(("/system/notepad.exe",))
    )

    assert service.effective_editor() == chosen


def test_with_nothing_remembered_the_machine_default_is_used() -> None:
    notepad = os.path.join("/system", "notepad.exe")
    service = a_service(
        paths=FakePaths(programs=(), system="/system"),
        probe=FakeProbe((notepad,)),
    )

    assert service.effective_editor().path == notepad


def test_the_control_can_act_on_a_default_nobody_chose() -> None:
    notepad = os.path.join("/system", "notepad.exe")
    service = a_service(
        paths=FakePaths(programs=(), system="/system"),
        probe=FakeProbe((notepad,)),
    )

    assert service.can_open_in_editor(a_skill())


def test_a_skill_opens_in_the_default_when_nothing_was_chosen() -> None:
    notepad = os.path.join("/system", "notepad.exe")
    launcher = FakeLauncher()
    service = a_service(
        launcher=launcher,
        paths=FakePaths(programs=(), system="/system"),
        probe=FakeProbe((notepad,)),
    )

    assert service.open_in_editor(a_skill())
    assert launcher.launched[0][0].path == notepad


def test_a_fresh_install_has_every_group_shut() -> None:
    assert a_service().opened_groups() == ()


def test_the_groups_a_reader_opens_are_remembered() -> None:
    store = FakeSettingsStore()
    service = a_service(store=store)

    service.remember_opened_groups(("Your skills",))

    assert service.opened_groups() == ("Your skills",)
    assert store.settings.opened_groups == ("Your skills",)
