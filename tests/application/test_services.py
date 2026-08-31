"""The questions the user interface asks, answered by the service."""

from __future__ import annotations

from skillsviewer.application.defaults import default_skills_root
from skillsviewer.application.services import SkillLibraryService
from skillsviewer.domain.catalogue import SkillCatalogue
from skillsviewer.domain.settings import EditorChoice, Settings

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
