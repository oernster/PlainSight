"""The import dialog: paste, Enter, stop safely, say plainly what went wrong."""

from __future__ import annotations

import threading
import time
from collections.abc import Callable

import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from plainsight.application.release_import import (
    ImportStage,
    NoPublishedReleases,
    RateLimited,
    ReleaseImportService,
)
from plainsight.domain import repository_address as parsing
from plainsight.domain.release import Release
from plainsight.ui import release_import_wording as wording
from plainsight.ui.release_import_dialog import ReleaseImportDialog
from tests.application.release_fakes import FakeCollectionStore, FakeReleaseSource

PASTED = "https://github.com/oernster/PlainSight/"
A_RELEASE = Release(source_id=1, tag="v1", published_at="2026-01-01T00:00:00Z")
PATIENCE_S = 5.0
TICK_S = 0.01


def wait_until(condition: Callable[[], bool]) -> None:
    """Let queued signals arrive until ``condition`` holds; fail if it never does."""
    deadline = time.monotonic() + PATIENCE_S
    while not condition():
        assert time.monotonic() < deadline, "waited too long"
        QApplication.processEvents()
        time.sleep(TICK_S)


class Held:
    """A gate the fake source waits at, so a test can act while it is busy."""

    def __init__(self) -> None:
        self.reached = threading.Event()
        self.release = threading.Event()

    def __call__(self) -> None:
        self.reached.set()
        self.release.wait(PATIENCE_S)


def a_dialog(
    source: FakeReleaseSource, store: FakeCollectionStore | None = None
) -> tuple[ReleaseImportDialog, list, FakeCollectionStore]:
    held = store if store is not None else FakeCollectionStore()
    imported: list = []
    dialog = ReleaseImportDialog(
        ReleaseImportService(source=source, store=held),
        lambda outcome, address: imported.append((outcome, address)),
    )
    dialog.show()
    QApplication.processEvents()
    return dialog, imported, held


def test_it_opens_focused_on_the_address_with_the_default_selected(
    application: QApplication,
) -> None:
    dialog, _imported, _store = a_dialog(FakeReleaseSource())

    assert dialog.focusWidget() is dialog.address_field
    assert dialog.address_field.selectedText() == wording.DEFAULT_ADDRESS


def test_a_paste_replaces_the_default_whole(application: QApplication) -> None:
    dialog, _imported, _store = a_dialog(FakeReleaseSource())
    QApplication.clipboard().setText(PASTED)

    QTest.keyClick(
        dialog.address_field, Qt.Key.Key_V, Qt.KeyboardModifier.ControlModifier
    )

    assert dialog.address_field.text() == PASTED


def test_the_tab_order_runs_field_import_cancel(application: QApplication) -> None:
    dialog, _imported, _store = a_dialog(FakeReleaseSource())

    chain = []
    widget = dialog.address_field
    for _step in range(len(("import", "cancel"))):
        widget = widget.nextInFocusChain()
        while not widget.focusPolicy() & Qt.FocusPolicy.TabFocus:
            widget = widget.nextInFocusChain()
        chain.append(widget)

    assert chain == [dialog.import_button, dialog.cancel_button]


def test_enter_in_the_field_imports(application: QApplication) -> None:
    source = FakeReleaseSource((A_RELEASE,))
    dialog, imported, _store = a_dialog(source)
    dialog.address_field.setText(PASTED)

    QTest.keyClick(dialog.address_field, Qt.Key.Key_Return)
    wait_until(lambda: bool(imported))

    assert len(source.asked) == 1
    assert imported[0][1].name == "PlainSight"
    assert not dialog.isVisible()


def test_a_refused_address_asks_nothing_of_the_network(
    application: QApplication,
) -> None:
    source = FakeReleaseSource((A_RELEASE,))
    dialog, _imported, _store = a_dialog(source)

    dialog.import_button.click()

    assert source.asked == []
    assert dialog.problem.isVisible()
    assert dialog.problem.text() == parsing.NO_OWNER
    assert dialog.isVisible()


def test_the_stages_are_stated_while_it_runs(application: QApplication) -> None:
    gate = Held()
    source = FakeReleaseSource((A_RELEASE,), before_answer=gate)
    dialog, imported, _store = a_dialog(source)
    dialog.address_field.setText(PASTED)

    dialog.start()
    gate.reached.wait(PATIENCE_S)
    QApplication.processEvents()

    assert dialog.running
    assert dialog.status.text() == wording.RETRIEVING
    assert not dialog.address_field.isEnabled()
    assert not dialog.import_button.isEnabled()
    gate.release.set()
    wait_until(lambda: bool(imported))


def test_cancel_while_retrieving_writes_nothing(application: QApplication) -> None:
    gate = Held()
    source = FakeReleaseSource((A_RELEASE,), before_answer=gate)
    dialog, imported, store = a_dialog(source)
    dialog.address_field.setText(PASTED)
    dialog.start()
    gate.reached.wait(PATIENCE_S)

    dialog.cancel_button.click()

    assert dialog.isVisible(), "it waits for the worker rather than vanishing"
    assert dialog.status.text() == wording.STOPPING
    gate.release.set()
    wait_until(lambda: not dialog.isVisible())
    assert store.commits == []
    assert imported == []


def test_escape_while_running_stops_rather_than_closes(
    application: QApplication,
) -> None:
    gate = Held()
    source = FakeReleaseSource((A_RELEASE,), before_answer=gate)
    dialog, _imported, store = a_dialog(source)
    dialog.address_field.setText(PASTED)
    dialog.start()
    gate.reached.wait(PATIENCE_S)

    QTest.keyClick(dialog, Qt.Key.Key_Escape)

    assert dialog.isVisible()
    gate.release.set()
    wait_until(lambda: not dialog.isVisible())
    assert store.commits == []


def test_escape_while_idle_closes(application: QApplication) -> None:
    dialog, _imported, _store = a_dialog(FakeReleaseSource())

    QTest.keyClick(dialog, Qt.Key.Key_Escape)

    assert not dialog.isVisible()


def test_writing_cannot_be_stopped_so_cancel_goes_grey(
    application: QApplication,
) -> None:
    dialog, _imported, _store = a_dialog(FakeReleaseSource())
    dialog._address = parsing.parse_repository_address(PASTED)

    dialog._show_stage(ImportStage.WRITING, 3)
    assert dialog.status.text() == wording.WRITING
    assert not dialog.cancel_button.isEnabled()

    dialog.reject()
    assert dialog.status.text() == wording.FINISHING
    assert dialog.isVisible()
    dialog._address = None


@pytest.mark.parametrize(
    ("problem", "words"),
    [
        (NoPublishedReleases(), "No published releases were found"),
        (RateLimited(), "limit on requests"),
        (ValueError("boom"), "stopped unexpectedly: boom"),
    ],
)
def test_a_problem_is_said_and_the_dialog_is_ready_again(
    application: QApplication, problem: Exception, words: str
) -> None:
    dialog, imported, store = a_dialog(FakeReleaseSource(problem=problem))
    dialog.address_field.setText(PASTED)

    dialog.start()
    wait_until(lambda: dialog.problem.isVisible())

    assert words in dialog.problem.text()
    assert dialog.isVisible()
    assert dialog.address_field.isEnabled()
    assert dialog.import_button.isEnabled()
    assert dialog.cancel_button.isEnabled()
    assert not dialog.running
    assert imported == [] and store.commits == []


def test_a_second_start_while_running_is_ignored(application: QApplication) -> None:
    gate = Held()
    source = FakeReleaseSource((A_RELEASE,), before_answer=gate)
    dialog, imported, _store = a_dialog(source)
    dialog.address_field.setText(PASTED)
    dialog.start()
    gate.reached.wait(PATIENCE_S)

    dialog.start()

    gate.release.set()
    wait_until(lambda: bool(imported))
    assert len(source.asked) == 1
