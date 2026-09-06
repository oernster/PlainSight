"""The opening state: no folder chosen, so nothing on this machine is read.

Asserted at the window rather than at the service, because the claim is about
the running application. The window builds, applies its appearance, refreshes
and re-reads on every activation; a walk started by any of those would be a
walk of somebody's home directory that nobody asked for.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from PySide6.QtCore import QEvent
from PySide6.QtWidgets import QApplication

from plainsight.application.services import LibraryService
from plainsight.domain.settings import Settings
from plainsight.infrastructure.renderer import DocumentHtmlRenderer
from plainsight.infrastructure.resources import BundledAssets
from plainsight.ui.main_window import MainWindow
from tests.application.fakes import (
    FakeLauncher,
    FakeOpener,
    FakePaths,
    FakeProbe,
    FakeRepository,
    FakeSettingsStore,
    a_folder,
)

A_HOME = "/home/oliver"


@pytest.fixture
def repository() -> FakeRepository:
    """A repository that would answer; it records every root it is asked for."""
    return FakeRepository({"/chosen": a_folder("chosen", "/chosen")})


@pytest.fixture
def fresh(
    application: QApplication, repository: FakeRepository
) -> Iterator[MainWindow]:
    """A window with nothing remembered, which is how a fresh install opens."""
    service = LibraryService(
        repository=repository,
        settings_store=FakeSettingsStore(Settings()),
        launcher=FakeLauncher(),
        opener=FakeOpener(),
        probe=FakeProbe(),
        paths=FakePaths(home=A_HOME),
    )
    window = MainWindow(service, DocumentHtmlRenderer(), BundledAssets())
    window.show()
    QApplication.processEvents()
    yield window
    window.close()
    window.deleteLater()
    QApplication.processEvents()


def test_no_folder_chosen_means_no_directory_is_read(
    fresh: MainWindow, repository: FakeRepository
) -> None:
    """The whole of it: the repository is never asked to look anywhere."""
    assert repository.roots_read == []


def test_the_tree_opens_empty(fresh: MainWindow) -> None:
    assert fresh.library_tree.folder_items() == []
    assert fresh.library_tree.document_items() == []


def test_the_pane_invites_a_choice_rather_than_reporting_an_empty_folder(
    fresh: MainWindow,
) -> None:
    """Two different facts: it has not looked, against it looked and found none."""
    said = fresh.document_view.toPlainText()

    assert "Choose a folder" in said
    assert "No documents here" not in said


def test_coming_back_to_the_window_still_reads_nothing(
    fresh: MainWindow, repository: FakeRepository
) -> None:
    """The library is re-read on every activation, so this is the common path."""
    fresh.changeEvent(QEvent(QEvent.Type.ActivationChange))
    QApplication.processEvents()

    assert repository.roots_read == []


def test_switching_the_appearance_leaves_the_invitation_showing(
    fresh: MainWindow,
) -> None:
    """A repaint re-renders whatever is open, which here is a message."""
    fresh.switch_appearance()

    assert "Choose a folder" in fresh.document_view.toPlainText()


def test_choosing_a_folder_reads_that_one_and_says_so(
    fresh: MainWindow, repository: FakeRepository
) -> None:
    fresh.library_tree.show_library(fresh._service.choose_root("/chosen"))
    fresh.show_document(fresh.library_tree.selected_document())

    assert repository.roots_read == ["/chosen"]
    assert [item.text(0) for item in fresh.library_tree.folder_items()] == [
        "chosen (1)"
    ]


def test_the_chooser_would_open_somewhere_the_user_already_keeps_files(
    fresh: MainWindow, repository: FakeRepository
) -> None:
    """Offered as a starting place; being offered reads nothing."""
    start = fresh._service.browse_from()

    assert start
    assert ".claude" not in start
    assert repository.roots_read == []
