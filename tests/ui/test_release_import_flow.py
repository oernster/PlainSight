"""From Import to reading: a real window, a real folder, the newest release open.

The source is a fake, so nothing leaves the machine; everything after it is the
application's own: the service, the store writing to a temporary directory, the
repository reading it back and the tree showing it.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication

from plainsight.__main__ import build_readers
from plainsight.application.release_import import ReleaseImportService
from plainsight.application.services import LibraryService
from plainsight.domain.release import Release
from plainsight.domain.repository_address import RepositoryAddress
from plainsight.infrastructure.document_repository import FileSystemDocumentRepository
from plainsight.infrastructure.release_collection_store import (
    FileSystemReleaseCollections,
)
from plainsight.infrastructure.renderer import DocumentHtmlRenderer
from plainsight.infrastructure.resources import BundledAssets
from plainsight.ui import release_import_dialog, release_import_wording
from plainsight.ui.main_window import MainWindow
from tests.application.fakes import (
    FakeLauncher,
    FakeOpener,
    FakePaths,
    FakeProbe,
    FakeSettingsStore,
)
from tests.application.release_fakes import FakeReleaseSource

ADDRESS = RepositoryAddress("oernster", "PlainSight")


def dated(number: int, month: int, **changes: object) -> Release:
    fields: dict[str, object] = {
        "source_id": number,
        "tag": f"v{number}.0",
        "published_at": f"2026-{month:02d}-01T00:00:00Z",
        "body": f"Notes for release {number}\n",
    }
    fields.update(changes)
    return Release(**fields)  # type: ignore[arg-type]


# Tags chosen so their names sort the opposite way to their dates.
RELEASES = (
    dated(1, 1, tag="zeta"),
    dated(2, 5, tag="alpha"),
    dated(3, 3, tag="mu"),
)


class Built:
    """A window with a release import behind it, plus the pieces to inspect."""

    def __init__(self, tmp_path: Path, source: FakeReleaseSource) -> None:
        self.settings = FakeSettingsStore()
        self.collections = FileSystemReleaseCollections(tmp_path / "imports")
        self.imports = ReleaseImportService(source=source, store=self.collections)
        service = LibraryService(
            repository=FileSystemDocumentRepository(build_readers()),
            settings_store=self.settings,
            launcher=FakeLauncher(),
            opener=FakeOpener(),
            probe=FakeProbe(),
            paths=FakePaths(),
        )
        self.window = MainWindow(
            service, DocumentHtmlRenderer(), BundledAssets(), None, self.imports
        )
        self.window.show()

    def run(self) -> None:
        """Import as the button would, with the modal part done inline."""
        outcome = self.imports.import_releases(ADDRESS, lambda *_a: None, lambda: False)
        release_import_dialog.open_imported(
            self.window,
            self.window._reading.open_collection,
            self.window.report_status,
            outcome,
            ADDRESS,
        )
        QApplication.processEvents()


@pytest.fixture
def built(application: QApplication, tmp_path: Path) -> Iterator[Built]:
    made = Built(tmp_path, FakeReleaseSource(RELEASES))
    yield made
    made.window.close()


def test_a_finished_import_opens_the_collection_on_its_newest_release(
    built: Built,
) -> None:
    built.run()

    root = built.collections.location(ADDRESS)
    assert built.settings.settings.documents_root == root
    rows = [item.text(0) for item in built.window.library_tree.document_items()]
    assert rows == ["2026-05-01_alpha.md", "2026-03-01_mu.md", "2026-01-01_zeta.md"]
    selected = built.window.library_tree.selected_document()
    assert selected is not None and selected.name == "2026-05-01_alpha.md"
    assert "Notes for release 2" in built.window.document_view.toPlainText()


def test_the_markdown_files_are_the_releases(built: Built) -> None:
    built.run()

    root = Path(built.collections.location(ADDRESS))
    newest = (root / "2026-05-01_alpha.md").read_text(encoding="utf-8")
    assert newest.startswith("# alpha\n\n**Tag:** alpha")
    assert newest.endswith("Notes for release 2\n")


def test_the_status_bar_says_what_was_imported(built: Built) -> None:
    built.run()

    assert built.window.statusBar().currentMessage() == (
        "Imported 3 releases of oernster/PlainSight"
    )


def test_a_refresh_with_an_edit_keeps_it_and_says_so(
    built: Built, monkeypatch: pytest.MonkeyPatch
) -> None:
    built.run()
    root = Path(built.collections.location(ADDRESS))
    (root / "2026-01-01_zeta.md").write_text("mine", encoding="utf-8")
    built.imports.source.releases_given = (  # type: ignore[attr-defined]
        dated(1, 1, tag="zeta", body="changed upstream\n"),
        *RELEASES[1:],
        dated(4, 7, tag="newest"),
    )
    notices: list[str] = []
    monkeypatch.setattr(
        release_import_dialog.QMessageBox,
        "information",
        lambda _parent, _title, text: notices.append(text),
    )

    built.run()

    assert (root / "2026-01-01_zeta.md").read_text(encoding="utf-8") == "mine"
    assert len(notices) == 1 and "2026-01-01_zeta.md" in notices[0]
    selected = built.window.library_tree.selected_document()
    assert selected is not None and selected.name == "2026-07-01_newest.md"
    assert built.window.statusBar().currentMessage() == (
        "Refreshed oernster/PlainSight: 1 new, 0 updated"
    )


def test_the_button_puts_the_dialog_up_and_opens_what_it_imported(
    built: Built, monkeypatch: pytest.MonkeyPatch
) -> None:
    outcome = built.imports.import_releases(ADDRESS, lambda *_a: None, lambda: False)

    def finish_at_once(dialog: release_import_dialog.ReleaseImportDialog) -> int:
        dialog._on_imported(outcome, ADDRESS)
        return 1

    monkeypatch.setattr(
        release_import_dialog.ReleaseImportDialog, "exec", finish_at_once
    )

    built.window.top_tray.import_releases_button.click()
    QApplication.processEvents()

    selected = built.window.library_tree.selected_document()
    assert selected is not None and selected.name == "2026-05-01_alpha.md"


def test_the_button_does_nothing_on_a_window_with_no_import(
    window: MainWindow, monkeypatch: pytest.MonkeyPatch
) -> None:
    called: list[object] = []
    monkeypatch.setattr(
        release_import_dialog, "import_releases", lambda *args: called.append(args)
    )

    window.top_tray.import_releases_button.click()

    assert called == []


def test_the_tray_button_says_what_it_does(built: Built) -> None:
    button = built.window.top_tray.import_releases_button

    assert button.toolTip() == "Import GitHub release notes"
    assert not button.icon().isNull()
    assert release_import_wording.TITLE == "Import GitHub Releases"
