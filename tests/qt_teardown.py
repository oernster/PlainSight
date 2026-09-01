"""Destroying Qt widgets between tests, in one place for both suites.

Closing a window hides it. `deleteLater` only POSTS a DeferredDelete event;
`QApplication.processEvents` does not deliver that class of event outside a
running event loop, so a teardown built from those two destroys nothing at all.
Measured: eight windows built and torn down that way left all eight alive at
304 widgets; one `sendPostedEvents` call took that to zero.

Two suites in this repository build real widgets: the application's, then the
setup program's. Both ran in one process carrying a teardown of their own, both
wrong in the same way, so the fix lives here rather than being written twice.
"""

from __future__ import annotations

from PySide6.QtCore import QCoreApplication, QEvent
from PySide6.QtWidgets import QApplication, QWidget


def destroy_all_widgets(application: QApplication) -> None:
    """Leave nothing alive, not merely nothing on screen."""
    for widget in list(application.topLevelWidgets()):
        if isinstance(widget, QWidget):
            widget.close()
            widget.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
