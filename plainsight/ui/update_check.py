"""The update check as the user meets it: quiet by default, plain when asked.

The check runs on a worker thread and its result crosses back on a signal
connected to a bound method of this object, which lives on the interface
thread. That is the whole reason this class exists: a signal connected to a
bare callable runs in the sender's thread; no widget may be touched from
there.
"""

from __future__ import annotations

import threading
from collections.abc import Callable

from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtWidgets import QMessageBox, QWidget

from ..application.services import LibraryService
from ..application.update import UpdateOutcome, UpdateService, UpdateStatus, outcome_for

# Late enough that the check never contends with the window appearing.
LAUNCH_DELAY_MS = 3000
HOURS_PER_DAY = 24
MINUTES_PER_HOUR = 60
SECONDS_PER_MINUTE = 60
MS_PER_SECOND = 1000
DAY_MS = HOURS_PER_DAY * MINUTES_PER_HOUR * SECONDS_PER_MINUTE * MS_PER_SECOND

DOWNLOAD_LABEL = "Download"
SKIP_LABEL = "Skip This Version"
LATER_LABEL = "Later"

UPDATE_TITLE = "Update available"
UP_TO_DATE_TITLE = "No update"
UNREACHABLE_TITLE = "Update check"

UP_TO_DATE_MESSAGE = "You are running the latest version."
UNREACHABLE_MESSAGE = "The update check could not reach GitHub. Please try again later."
NO_BROWSER_MESSAGE = "Could not open a browser for the download"


def update_message(application_name: str, status: UpdateStatus) -> str:
    """What the prompt says it found."""
    return (
        f"{application_name} {status.latest} is available. "
        f"You are running {status.current}."
    )


class UpdateCheckController(QObject):
    """Runs the check off the interface thread and reports what it found."""

    _result_ready = Signal(object, bool)

    def __init__(
        self,
        window: QWidget,
        updates: UpdateService,
        library: LibraryService,
        application_name: str,
        report_failure: Callable[[str], None] | None = None,
    ) -> None:
        super().__init__(window if isinstance(window, QObject) else None)
        self._window = window
        self._updates = updates
        self._library = library
        self._name = application_name
        self._report_failure = report_failure
        # A bound method of an object living on the interface thread, so Qt
        # queues the delivery rather than running the slot in the worker.
        self._result_ready.connect(self._apply_result)

        # Both timers are children of this controller rather than free
        # standing, so they die with it. A bare QTimer.singleShot outlives the
        # window it was armed from and fires into whatever is running three
        # seconds later; measured, not assumed, it hung the test run.
        self._launch = QTimer(self)
        self._launch.setSingleShot(True)
        self._launch.setInterval(LAUNCH_DELAY_MS)
        self._launch.timeout.connect(self.check_automatically)
        self._daily = QTimer(self)
        self._daily.setInterval(DAY_MS)
        self._daily.timeout.connect(self.check_automatically)

    def start(self) -> None:
        """Begin checking: shortly after the window shows, then daily.

        Separate from construction on purpose. A constructor that starts work
        cannot be built without also starting it, which is exactly what a test
        needs to do.
        """
        self._launch.start()
        self._daily.start()

    def check_automatically(self) -> None:
        """The check nobody asked for: honours the skip, silent about failure."""
        self._start(self._library.skipped_update_version(), manual=False)

    def check_manually(self) -> None:
        """The check the user asked for: ignores the skip, reports everything."""
        self._start("", manual=True)

    def _start(self, skipped: str, manual: bool) -> None:
        """Ask the source on a worker thread."""
        thread = threading.Thread(target=self._run, args=(skipped, manual), daemon=True)
        thread.start()

    def _run(self, skipped: str, manual: bool) -> None:
        """The worker body. Nothing here touches a widget."""
        self._result_ready.emit(self._updates.check(skipped), manual)

    def _apply_result(self, status: UpdateStatus, manual: bool) -> None:
        """Report the result. This runs on the interface thread."""
        outcome = outcome_for(status, manual)
        if outcome is UpdateOutcome.SILENT:
            return
        if outcome is UpdateOutcome.PROMPT:
            self._offer(status)
            return
        title, message = (
            (UP_TO_DATE_TITLE, UP_TO_DATE_MESSAGE)
            if outcome is UpdateOutcome.UP_TO_DATE
            else (UNREACHABLE_TITLE, UNREACHABLE_MESSAGE)
        )
        self._say(title, message)

    def _say(self, title: str, message: str) -> None:
        """One plain sentence in a box with a single way out."""
        box = QMessageBox(self._window)
        box.setWindowTitle(title)
        box.setText(message)
        box.setStandardButtons(QMessageBox.StandardButton.Ok)
        box.exec()

    def _offer(self, status: UpdateStatus) -> None:
        """Download, skip this one for good, else be asked again tomorrow."""
        box = QMessageBox(self._window)
        box.setWindowTitle(UPDATE_TITLE)
        box.setText(update_message(self._name, status))
        download = box.addButton(DOWNLOAD_LABEL, QMessageBox.ButtonRole.AcceptRole)
        skip = box.addButton(SKIP_LABEL, QMessageBox.ButtonRole.DestructiveRole)
        box.addButton(LATER_LABEL, QMessageBox.ButtonRole.RejectRole)
        box.setDefaultButton(download)
        box.exec()

        pressed = box.clickedButton()
        if pressed is download:
            self._download(status)
        elif pressed is skip:
            self._library.skip_update_version(status.latest)

    def _download(self, status: UpdateStatus) -> None:
        """Hand the platform's own file to the desktop; else the release page.

        The application downloads nothing itself: the address goes out and the
        browser does the fetching.
        """
        address = status.download_url or status.page_url
        if address is None:
            return
        if not self._library.open_page(address) and self._report_failure is not None:
            self._report_failure(NO_BROWSER_MESSAGE)


def install_update_check(
    window: QWidget,
    updates: UpdateService,
    library: LibraryService,
    application_name: str,
    report_failure: Callable[[str], None] | None = None,
) -> UpdateCheckController:
    """Attach the check to a window, so the window itself wires nothing."""
    controller = UpdateCheckController(
        window, updates, library, application_name, report_failure
    )
    controller.setObjectName("UpdateCheckController")
    controller.start()
    return controller
