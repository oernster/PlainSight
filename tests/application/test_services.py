"""The questions the user interface asks, answered by the service."""

from __future__ import annotations

import os

from plainsight.application.defaults import default_root
from plainsight.application.services import LibraryService
from plainsight.domain.library import Folder
from plainsight.domain.settings import (
    Appearance,
    EditorChoice,
    FontSize,
    Settings,
)

from .fakes import (
    FakeLauncher,
    FakeOpener,
    FakePaths,
    FakeProbe,
    FakeRepository,
    FakeSettingsStore,
    a_document,
    a_folder,
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
) -> LibraryService:
    return LibraryService(
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

    assert service.current_root() == default_root(paths)


def test_loading_reads_the_current_root() -> None:
    repository = FakeRepository()
    store = FakeSettingsStore(Settings(documents_root="/elsewhere"))

    a_service(repository=repository, store=store).load()

    assert repository.roots_read[0] == "/elsewhere"


def test_choosing_a_root_remembers_it_and_reads_it() -> None:
    repository = FakeRepository({"/chosen": a_folder("chosen", "/chosen")})
    store = FakeSettingsStore()

    library = a_service(repository=repository, store=store).choose_root("/chosen")

    assert store.settings.documents_root == "/chosen"
    assert "/chosen" in repository.roots_read
    assert library.document_count == 1


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
    store = FakeSettingsStore(Settings(documents_root="/elsewhere"))

    assert a_service(store=store).settings().documents_root == "/elsewhere"


def test_no_document_selected_means_the_editor_control_can_do_nothing() -> None:
    store = FakeSettingsStore(Settings(editor=AN_EDITOR))
    probe = FakeProbe(present=(AN_EDITOR.path,))

    assert not a_service(store=store, probe=probe).can_open_in_editor(None)


def test_no_editor_chosen_means_the_editor_control_can_do_nothing() -> None:
    assert not a_service().can_open_in_editor(a_document())


def test_an_editor_that_has_gone_means_the_control_can_do_nothing() -> None:
    store = FakeSettingsStore(Settings(editor=AN_EDITOR))

    service = a_service(store=store, probe=FakeProbe(present=()))

    assert not service.can_open_in_editor(a_document())


def test_a_document_plus_an_editor_that_is_there_enables_the_control() -> None:
    store = FakeSettingsStore(Settings(editor=AN_EDITOR))
    probe = FakeProbe(present=(AN_EDITOR.path,))

    assert a_service(store=store, probe=probe).can_open_in_editor(a_document())


def test_opening_hands_the_document_to_the_chosen_editor() -> None:
    store = FakeSettingsStore(Settings(editor=AN_EDITOR))
    launcher = FakeLauncher()
    document = a_document()

    assert a_service(store=store, launcher=launcher).open_in_editor(document)
    assert launcher.launched == [(AN_EDITOR, document.path)]


def test_opening_without_an_editor_reports_that_it_did_nothing() -> None:
    launcher = FakeLauncher()

    assert not a_service(launcher=launcher).open_in_editor(a_document())
    assert launcher.launched == []


def test_a_desktop_that_declines_the_editor_is_reported() -> None:
    store = FakeSettingsStore(Settings(editor=AN_EDITOR))

    service = a_service(store=store, launcher=FakeLauncher(accepts=False))

    assert not service.open_in_editor(a_document())


def test_the_donation_address_is_handed_over_untouched() -> None:
    opener = FakeOpener()

    assert a_service(opener=opener).open_donation_page(A_DONATION_ADDRESS)
    assert opener.opened == [A_DONATION_ADDRESS]


def test_a_desktop_that_declines_the_donation_page_is_reported() -> None:
    service = a_service(opener=FakeOpener(accepts=False))

    assert not service.open_donation_page(A_DONATION_ADDRESS)


def test_loading_reads_the_plugins_tree_beside_the_root_too() -> None:
    repository = FakeRepository()
    chosen = os.path.join("home", ".claude", "skills")
    store = FakeSettingsStore(Settings(documents_root=chosen))

    a_service(repository=repository, store=store).load()

    assert repository.roots_read == [chosen, os.path.join("home", ".claude", "plugins")]


def test_both_trees_arrive_as_one_library_in_the_order_they_are_shown() -> None:
    """The chosen folder first, the plugins tree beside it second."""
    skills = os.path.join("home", ".claude", "skills")
    plugins = os.path.join("home", ".claude", "plugins")
    repository = FakeRepository(
        {
            skills: a_folder("skills", skills, "SKILL.md"),
            plugins: a_folder("plugins", plugins, "SKILL.md"),
        }
    )
    store = FakeSettingsStore(Settings(documents_root=skills))

    library = a_service(repository=repository, store=store).load()

    assert library.document_count == 2
    assert [root.name for root in library.roots] == ["skills", "plugins"]


def test_a_tree_that_is_not_there_contributes_no_root() -> None:
    """Browse anywhere with no plugins beside it and one tree is what shows."""
    repository = FakeRepository({"/notes": a_folder("notes", "/notes")})
    store = FakeSettingsStore(Settings(documents_root="/notes"))

    library = a_service(repository=repository, store=store).load()

    assert [root.name for root in library.roots] == ["notes"]


def test_a_tree_that_leads_to_no_document_contributes_no_root() -> None:
    """A heading over nothing is worse than no heading: it promises content."""
    repository = FakeRepository({"/notes": Folder.of("notes", "/notes")})
    store = FakeSettingsStore(Settings(documents_root="/notes"))

    library = a_service(repository=repository, store=store).load()

    assert library.roots == ()
    assert library.is_empty


def test_choosing_a_root_reads_the_plugins_beside_that_one() -> None:
    repository = FakeRepository()
    chosen = os.path.join("other", ".claude", "skills")

    a_service(repository=repository).choose_root(chosen)

    assert repository.roots_read == [
        chosen,
        os.path.join("other", ".claude", "plugins"),
    ]


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

    assert service.can_open_in_editor(a_document())


def test_a_document_opens_in_the_default_when_nothing_was_chosen() -> None:
    notepad = os.path.join("/system", "notepad.exe")
    launcher = FakeLauncher()
    service = a_service(
        launcher=launcher,
        paths=FakePaths(programs=(), system="/system"),
        probe=FakeProbe((notepad,)),
    )

    assert service.open_in_editor(a_document())
    assert launcher.launched[0][0].path == notepad


def test_a_fresh_install_has_every_folder_shut() -> None:
    assert a_service().opened_folders() == ()


def test_the_folders_a_reader_opens_are_remembered() -> None:
    store = FakeSettingsStore()
    service = a_service(store=store)

    service.remember_opened_folders(("/skills/prose",))

    assert service.opened_folders() == ("/skills/prose",)
    assert store.settings.opened_folders == ("/skills/prose",)


def test_nothing_is_skipped_until_something_is() -> None:
    assert a_service().skipped_update_version() == ""


def test_a_skipped_release_is_remembered() -> None:
    store = FakeSettingsStore()
    service = a_service(store=store)

    service.skip_update_version("0.2.0")

    assert service.skipped_update_version() == "0.2.0"
    assert store.settings.skipped_update_version == "0.2.0"


def test_skipping_a_release_keeps_everything_else_remembered() -> None:
    store = FakeSettingsStore(Settings(documents_root="/skills", editor=AN_EDITOR))
    service = a_service(store=store)

    service.skip_update_version("0.2.0")

    assert store.settings.documents_root == "/skills"
    assert store.settings.editor == AN_EDITOR


def test_a_page_goes_to_the_desktop_and_says_whether_it_was_taken() -> None:
    opener = FakeOpener(accepts=True)
    service = a_service(opener=opener)

    assert service.open_page("https://example.invalid/release") is True
    assert opener.opened == ["https://example.invalid/release"]


def test_a_page_the_desktop_declines_is_reported_as_declined() -> None:
    service = a_service(opener=FakeOpener(accepts=False))

    assert service.open_page("https://example.invalid/release") is False


def test_text_starts_at_the_middle_size() -> None:
    assert a_service().font_size() is FontSize.MEDIUM


def test_cycling_the_text_size_steps_it_and_remembers_it() -> None:
    store = FakeSettingsStore()
    service = a_service(store=store)

    assert service.cycle_font_size() is FontSize.LARGE
    assert store.settings.font_size is FontSize.LARGE
    assert service.font_size() is FontSize.LARGE


def test_cycling_past_the_largest_returns_to_the_smallest() -> None:
    service = a_service(
        store=FakeSettingsStore(Settings(font_size=FontSize.EXTRA_LARGE))
    )

    assert service.cycle_font_size() is FontSize.MEDIUM


def test_cycling_the_text_size_keeps_everything_else_remembered() -> None:
    store = FakeSettingsStore(Settings(documents_root="/skills", editor=AN_EDITOR))
    service = a_service(store=store)

    service.cycle_font_size()

    assert store.settings.documents_root == "/skills"
    assert store.settings.editor == AN_EDITOR
