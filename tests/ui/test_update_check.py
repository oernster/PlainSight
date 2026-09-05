"""The update check as the window carries it: the menu, the ring and the thread."""

from __future__ import annotations

import threading
import time
from collections.abc import Iterator
from pathlib import Path

import pytest
from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QKeyEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QWidget

from plainsight.__main__ import build_readers
from plainsight.application.services import LibraryService
from plainsight.application.update import (
    ReleaseAsset,
    ReleaseInfo,
    UpdateService,
    UpdateStatus,
)
from plainsight.domain.settings import Settings
from plainsight.infrastructure.document_repository import FileSystemDocumentRepository
from plainsight.infrastructure.renderer import DocumentHtmlRenderer
from plainsight.infrastructure.resources import BundledAssets
from plainsight.ui.main_window import MainWindow
from plainsight.ui.top_tray import ABOUT_ITEM, CHECK_UPDATES_ITEM, GUIDE_ITEM, TopTray
from plainsight.ui.update_check import UpdateCheckController, update_message
from tests.application.fakes import (
    FakeLauncher,
    FakeOpener,
    FakePaths,
    FakeProbe,
    FakeSettingsStore,
)

A_PAGE = "https://example.test/releases"
SPIN_SECONDS = 2.0
SPIN_STEP_MS = 10


class FakeSource:
    """Answers with one release and records what it was asked."""

    def __init__(self, release: ReleaseInfo | None) -> None:
        self._release = release

    def latest_release(self) -> ReleaseInfo | None:
        return self._release


def a_release(version: str = "9.9.9") -> ReleaseInfo:
    return ReleaseInfo(
        version=version,
        page_url=A_PAGE,
        assets=(ReleaseAsset(name="PlainSightSetup.exe", download_url="the-exe"),),
    )


def an_update_service(release: ReleaseInfo | None) -> UpdateService:
    """A service over one release. None means a source that cannot be asked.

    There is deliberately no default: a helper that read None as its own
    default silently turned every unreachable case into a reachable one.
    """
    return UpdateService(
        source=FakeSource(release), current_version="0.1.0", platform_key="windows"
    )


class RecordingController(UpdateCheckController):
    """The real controller with its two boxes replaced by a record.

    A message box would block on exec, so what is measured here is which call
    was reached and on which thread it ran, never a rendered dialog.
    """

    def __init__(self, *args: object, **kwargs: object) -> None:
        self.offered: list[UpdateStatus] = []
        self.said: list[tuple[str, str]] = []
        self.threads: list[str] = []
        super().__init__(*args, **kwargs)  # type: ignore[arg-type]

    def _offer(self, status: UpdateStatus) -> None:
        self.threads.append(threading.current_thread().name)
        self.offered.append(status)

    def _say(self, title: str, message: str) -> None:
        self.threads.append(threading.current_thread().name)
        self.said.append((title, message))


def spin_until(predicate: object) -> bool:
    """Run the event loop until the predicate holds; give up saying so."""
    deadline = time.monotonic() + SPIN_SECONDS
    while time.monotonic() < deadline:
        QApplication.processEvents()
        if predicate():  # type: ignore[operator]
            return True
        QTest.qWait(SPIN_STEP_MS)
    return False


@pytest.fixture
def library(documents_root: Path, store: FakeSettingsStore) -> LibraryService:
    store.settings = Settings(documents_root=str(documents_root))
    return LibraryService(
        repository=FileSystemDocumentRepository(build_readers()),
        settings_store=store,
        launcher=FakeLauncher(),
        opener=FakeOpener(),
        probe=FakeProbe(),
        paths=FakePaths(),
    )


@pytest.fixture
def checked_window(
    application: QApplication,
    library: LibraryService,
) -> Iterator[MainWindow]:
    # The release matches the running version on purpose. This window carries a
    # real controller whose automatic check fires three seconds in; a real
    # controller that finds an update opens a real message box, which blocks
    # the whole run rather than failing it. Measured, not guessed: it hung here.
    main = MainWindow(
        library,
        DocumentHtmlRenderer(),
        BundledAssets(),
        an_update_service(a_release("0.1.0")),
    )
    main.show()
    yield main
    main.close()
    main.deleteLater()
    QApplication.processEvents()


@pytest.fixture
def host(application: QApplication) -> Iterator[QWidget]:
    """A bare parent for a controller.

    Deliberately not the main window: a controller needs something to parent
    to and nothing more. Building a whole window for each of these cost several
    seconds apiece late in the run, measured rather than supposed.
    """
    widget = QWidget()
    yield widget
    widget.close()
    widget.deleteLater()
    QApplication.processEvents()


def a_controller(
    host: QWidget, library: LibraryService, release: ReleaseInfo | None
) -> RecordingController:
    return RecordingController(
        host, an_update_service(release), library, "PlainSight", None
    )


def test_the_help_button_offers_the_guide_about_and_a_check_in_that_order(
    window: MainWindow,
) -> None:
    """The guide leads it: opening this menu is usually asking how it works."""
    labels = [action.text() for action in window.top_tray.help_menu.actions()]

    assert labels == [GUIDE_ITEM, ABOUT_ITEM, CHECK_UPDATES_ITEM]


def test_pressing_help_drops_the_menu_rather_than_opening_a_dialog(
    window: MainWindow,
) -> None:
    window.top_tray.help_button.click()

    assert window.top_tray.help_menu.isVisible()
    window.top_tray.help_menu.close()


def test_the_ring_stands_aside_while_the_menu_is_open(window: MainWindow) -> None:
    """The ring must not consume the keys an open menu is there to receive.

    Measured on what the filter answers rather than on where focus lands.
    While a popup holds the grab Qt refuses the focus change anyway, so a test
    watching focus passes with the guard deleted and proves nothing; this one
    was written that way first and did not bite when the guard was removed.
    """
    window.activateWindow()
    QApplication.processEvents()
    tab = QKeyEvent(
        QEvent.Type.KeyPress, Qt.Key.Key_Tab, Qt.KeyboardModifier.NoModifier
    )
    assert window.navigator.eventFilter(window, tab) is True

    window.top_tray.help_button.click()
    assert window.top_tray.help_menu.isVisible()

    assert window.navigator.eventFilter(window, tab) is False
    window.top_tray.help_menu.close()


def test_each_menu_item_calls_its_own_handler(application: QApplication) -> None:
    pressed: list[str] = []
    tray = TopTray(
        None,
        BundledAssets(),
        on_choose_folder=lambda: pressed.append("folder"),
        on_open_file=lambda: pressed.append("file"),
        on_choose_editor=lambda: pressed.append("choose"),
        on_open_in_editor=lambda: pressed.append("open"),
        on_cycle_font_size=lambda: pressed.append("font"),
        on_switch_appearance=lambda: pressed.append("appearance"),
        on_guide=lambda: pressed.append("guide"),
        on_about=lambda: pressed.append("about"),
        on_check_updates=lambda: pressed.append("updates"),
    )

    tray.guide_action.trigger()
    tray.about_action.trigger()
    tray.check_updates_action.trigger()

    assert pressed == ["guide", "about", "updates"]
    tray.deleteLater()


def test_a_window_built_with_no_update_service_has_no_check(
    window: MainWindow,
) -> None:
    assert window.update_check is None
    window.check_for_updates()  # asks nothing, says nothing, does not raise


def test_a_window_built_with_an_update_service_has_one(
    checked_window: MainWindow,
) -> None:
    assert checked_window.update_check is not None


def test_the_result_is_reported_on_the_interface_thread(
    host: QWidget, library: LibraryService
) -> None:
    """The whole reason the controller exists; measured rather than assumed."""
    controller = a_controller(host, library, a_release())

    controller.check_manually()

    assert spin_until(lambda: bool(controller.offered))
    assert controller.threads == [threading.main_thread().name]


def test_a_newer_release_is_offered_with_its_file(
    host: QWidget, library: LibraryService
) -> None:
    controller = a_controller(host, library, a_release("9.9.9"))

    controller.check_manually()

    assert spin_until(lambda: bool(controller.offered))
    status = controller.offered[0]
    assert status.latest == "9.9.9"
    assert status.download_url == "the-exe"


def test_an_up_to_date_check_the_user_asked_for_says_so(
    host: QWidget, library: LibraryService
) -> None:
    controller = a_controller(host, library, a_release("0.1.0"))

    controller.check_manually()

    assert spin_until(lambda: bool(controller.said))
    assert controller.said[0][1] == "You are running the latest version."


def test_an_unreachable_check_the_user_asked_for_says_so(
    host: QWidget, library: LibraryService
) -> None:
    controller = a_controller(host, library, None)

    controller.check_manually()

    assert spin_until(lambda: bool(controller.said))
    assert "could not reach GitHub" in controller.said[0][1]


def test_an_automatic_check_that_finds_nothing_says_nothing(
    host: QWidget, library: LibraryService
) -> None:
    """The silent branch, proved by a probe that fires after it would have."""
    controller = a_controller(host, library, None)
    seen: list[bool] = []
    controller._result_ready.connect(lambda *_unused: seen.append(True))

    controller.check_automatically()

    assert spin_until(lambda: bool(seen))
    assert controller.said == []
    assert controller.offered == []


def test_an_automatic_check_honours_a_skipped_release(
    host: QWidget, library: LibraryService
) -> None:
    library.skip_update_version("9.9.9")
    controller = a_controller(host, library, a_release("9.9.9"))
    seen: list[bool] = []
    controller._result_ready.connect(lambda *_unused: seen.append(True))

    controller.check_automatically()

    assert spin_until(lambda: bool(seen))
    assert controller.offered == []


def test_a_check_the_user_asked_for_ignores_a_skipped_release(
    host: QWidget, library: LibraryService
) -> None:
    library.skip_update_version("9.9.9")
    controller = a_controller(host, library, a_release("9.9.9"))

    controller.check_manually()

    assert spin_until(lambda: bool(controller.offered))
    assert controller.offered[0].latest == "9.9.9"


def test_the_prompt_names_both_versions() -> None:
    status = UpdateStatus(current="0.1.0", latest="0.2.0", update_available=True)

    assert update_message("PlainSight", status) == (
        "PlainSight 0.2.0 is available. You are running 0.1.0."
    )
