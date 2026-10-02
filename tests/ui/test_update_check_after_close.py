"""An update check whose window has gone before its answer comes back.

The controller is a child of the window, so it goes when the window does. If
that happens while the worker is still waiting on GitHub, its emit raises
"Signal source has been deleted" on a thread nothing catches; this test makes
it happen and measured exactly that before the fix. Quitting is not such a
path: a probe of the real quit sequence on 2026-10-02 found the controller
still alive when the answer arrived. This is hardening rather than a fix for
anything a reader has met. Nobody is left to tell, so the answer is dropped;
what must not happen is an exception escaping a thread this application
started.
"""

from __future__ import annotations

import threading

import shiboken6
from PySide6.QtWidgets import QApplication, QWidget

from plainsight.application.services import LibraryService
from plainsight.application.update import ReleaseInfo
from plainsight.ui.update_check import UpdateCheckController
from tests.ui.update_support import a_service_over

# Far longer than a check against a stand-in takes, so only a hang reaches it.
WAIT_SECONDS = 5


class HeldSource:
    """A release source that answers only once the test lets it."""

    def __init__(self) -> None:
        self.asked = threading.Event()
        self.answer = threading.Event()
        self.worker: threading.Thread | None = None

    def latest_release(self) -> ReleaseInfo | None:
        """Say it has been asked, then wait to be allowed to answer."""
        self.worker = threading.current_thread()
        self.asked.set()
        self.answer.wait(WAIT_SECONDS)
        return None


def test_an_answer_with_nowhere_to_go_is_dropped_not_raised(
    application: QApplication, library: LibraryService, monkeypatch
) -> None:
    escaped: list[BaseException | None] = []
    monkeypatch.setattr(
        threading, "excepthook", lambda raised: escaped.append(raised.exc_value)
    )
    source = HeldSource()
    window = QWidget()
    controller = UpdateCheckController(
        window, a_service_over(source), library, "PlainSight", None
    )
    controller.check_manually()
    assert source.asked.wait(WAIT_SECONDS), "the check never started"
    shiboken6.delete(window)
    assert not shiboken6.isValid(controller), "the window kept its controller"
    source.answer.set()
    source.worker.join(WAIT_SECONDS)
    assert not source.worker.is_alive(), "the check never finished"
    assert escaped == []
