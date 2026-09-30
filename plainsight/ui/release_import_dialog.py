"""The release import as the reader meets it: paste, Enter, then reading.

The field opens focused with its whole default selected, so the paste that
follows replaces it; Enter imports; Escape cancels. The work runs on a worker
thread and its results cross back on signals connected to bound methods of
this dialog, which lives on the interface thread, for the reason the update
check gives: a signal connected to a bare callable runs in the sender's thread;
no widget may be touched from there.

The dialog never closes while the worker runs. Cancel or Escape asks the
worker to stop and waits for it to say it has, so the worker can never report
to a dialog that is no longer there. Stopping is honoured until writing starts
and not after, which is the service's own rule.
"""

from __future__ import annotations

import threading
from collections.abc import Callable

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..application.release_import import (
    ImportCancelled,
    ImportOutcome,
    ImportStage,
    ReleaseImportService,
)
from ..domain.repository_address import (
    InvalidRepositoryAddress,
    RepositoryAddress,
    parse_repository_address,
)
from . import release_import_wording as wording
from .widgets import FirstStopDialog

MINIMUM_WIDTH_PX = 480
EXAMPLE_NAME = "ImportExample"
PROBLEM_NAME = "ImportProblem"
STATUS_NAME = "ImportStatus"


class ReleaseImportDialog(FirstStopDialog):
    """Asks which repository, runs the import, reports how it ended."""

    _progressed = Signal(object, int)
    _finished = Signal(object)

    def __init__(
        self,
        service: ReleaseImportService,
        on_imported: Callable[[ImportOutcome, RepositoryAddress], None],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._service = service
        self._on_imported = on_imported
        self._stop = threading.Event()
        self._address: RepositoryAddress | None = None
        self.setWindowTitle(wording.TITLE)
        self.setMinimumWidth(MINIMUM_WIDTH_PX)

        label = QLabel(wording.FIELD_LABEL, self)
        self.address_field = QLineEdit(wording.DEFAULT_ADDRESS, self)
        self.address_field.setAccessibleName(wording.FIELD_LABEL)
        label.setBuddy(self.address_field)
        # Beneath the field rather than inside it: the field already holds the
        # default the paste replaces, so a placeholder there would never show.
        self.example = QLabel(wording.EXAMPLE, self)
        self.example.setObjectName(EXAMPLE_NAME)
        self.problem = QLabel("", self)
        self.problem.setObjectName(PROBLEM_NAME)
        self.problem.setWordWrap(True)
        self.problem.setVisible(False)
        self.status = QLabel("", self)
        self.status.setObjectName(STATUS_NAME)
        self.status.setVisible(False)
        self.import_button = QPushButton(wording.IMPORT_LABEL, self)
        self.cancel_button = QPushButton(wording.CANCEL_LABEL, self)
        for button in (self.import_button, self.cancel_button):
            button.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        # The default, so Enter in the field imports: the dialog hands Enter
        # to its default button, which is the one route and cannot fire twice.
        self.import_button.setDefault(True)
        self.import_button.clicked.connect(self.start)
        self.cancel_button.clicked.connect(self.reject)

        buttons = QHBoxLayout()
        buttons.addStretch()
        buttons.addWidget(self.import_button)
        buttons.addWidget(self.cancel_button)
        column = QVBoxLayout(self)
        column.addWidget(label)
        column.addWidget(self.address_field)
        column.addWidget(self.example)
        column.addWidget(self.problem)
        column.addWidget(self.status)
        column.addLayout(buttons)

        self._progressed.connect(self._show_stage)
        self._finished.connect(self._finish)

    @property
    def running(self) -> bool:
        """Whether an import is under way now."""
        return self._address is not None

    def showEvent(self, event: object) -> None:
        """Open on the field with its whole default selected, ready to paste over."""
        super().showEvent(event)
        self.address_field.setFocus(Qt.FocusReason.TabFocusReason)
        self.address_field.selectAll()

    def start(self) -> None:
        """Read the address, then import it off the interface thread.

        An address that names no repository is answered here and nothing is
        asked of the network at all.
        """
        if self.running:
            return
        try:
            address = parse_repository_address(self.address_field.text())
        except InvalidRepositoryAddress as refusal:
            self._say(str(refusal))
            return
        self._address = address
        self._stop.clear()
        self.problem.setVisible(False)
        self.address_field.setEnabled(False)
        self.import_button.setEnabled(False)
        self._show_stage(ImportStage.RETRIEVING, 0)
        worker = threading.Thread(target=self._run, args=(address,), daemon=True)
        worker.start()

    def reject(self) -> None:
        """Close when idle; while running, ask the worker to stop and wait.

        Cancel, Escape and the window's own close button all arrive here.
        """
        if not self.running:
            super().reject()
            return
        self._stop.set()
        self.cancel_button.setEnabled(False)
        stopping = self.status.text() != wording.WRITING
        self.status.setText(wording.STOPPING if stopping else wording.FINISHING)

    def _run(self, address: RepositoryAddress) -> None:
        """The worker body. Nothing here touches a widget.

        Every failure is carried back rather than raised, including one nobody
        foresaw: an exception ending this thread would leave the dialog waiting
        for an answer that never comes.
        """
        try:
            result: object = self._service.import_releases(
                address, self._progressed.emit, self._stop.is_set
            )
        except Exception as problem:  # noqa: BLE001 - reported, see docstring
            result = problem
        self._finished.emit(result)

    def _show_stage(self, stage: ImportStage, count: int) -> None:
        """Say what the import is doing. This runs on the interface thread.

        Once writing starts it cannot be stopped, so Cancel goes grey rather
        than offering something it could not do.
        """
        if self._stop.is_set():
            return
        self.status.setText(wording.stage_message(stage, count))
        self.status.setVisible(True)
        if stage is ImportStage.WRITING:
            self.cancel_button.setEnabled(False)

    def _finish(self, result: object) -> None:
        """Hand a finished import on, close on a stop, else say what went wrong."""
        address = self._address
        self._address = None
        if isinstance(result, ImportOutcome) and address is not None:
            self.accept()
            self._on_imported(result, address)
            return
        if isinstance(result, ImportCancelled):
            super().reject()
            return
        self.status.setVisible(False)
        self.address_field.setEnabled(True)
        self.import_button.setEnabled(True)
        self.cancel_button.setEnabled(True)
        self._say(wording.problem_message(result))  # type: ignore[arg-type]
        self.address_field.setFocus(Qt.FocusReason.OtherFocusReason)

    def _say(self, message: str) -> None:
        """Show why the import did not happen, beneath the field."""
        self.problem.setText(message)
        self.problem.setVisible(True)


def open_imported(
    window: QWidget,
    open_collection: Callable[[str, str], None],
    report: Callable[[str], None],
    outcome: ImportOutcome,
    address: RepositoryAddress,
) -> None:
    """Read the imported folder, land on its newest release, say what changed.

    Anything kept rather than overwritten is said in a box of its own, since a
    status line that vanishes in seconds is no place to tell somebody their
    edits were protected.
    """
    open_collection(outcome.root, outcome.newest)
    report(wording.outcome_summary(outcome, f"{address.owner}/{address.name}"))
    notice = wording.kept_notice(outcome)
    if notice:
        QMessageBox.information(window, wording.TITLE, notice)


def import_releases(
    window: QWidget,
    service: ReleaseImportService,
    open_collection: Callable[[str, str], None],
    report: Callable[[str], None],
) -> None:
    """Put the dialog up; open whatever it imports once it has closed."""
    imported: list[tuple[ImportOutcome, RepositoryAddress]] = []
    ReleaseImportDialog(
        service, lambda outcome, address: imported.append((outcome, address)), window
    ).exec()
    for outcome, address in imported:
        open_imported(window, open_collection, report, outcome, address)
