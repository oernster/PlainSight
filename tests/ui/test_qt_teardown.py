"""Tearing a widget down has to destroy it, not merely hide it.

This is the guard on `tests.qt_teardown`. The teardown both Qt suites used to
have closed each window and called `deleteLater`, then `processEvents`.
`deleteLater` only POSTS a DeferredDelete event and `processEvents` does not
deliver that class of event outside a running event loop, so nothing was ever
destroyed and every widget either suite built stayed in the application.

That is not a tidiness point. It crashed the run. Measured on this machine: the
whole suite died with an access violation five times in fifteen, always inside
`QApplication.setStyleSheet`, which has to walk every widget the application
owns. With the teardown fixed the same suite ran twenty five times without a
crash; putting the old teardown back into the setup program's fixtures alone
brought it straight back at ten in twenty.
"""

from __future__ import annotations

from PySide6.QtWidgets import QApplication, QWidget

from tests.qt_teardown import destroy_all_widgets

A_FEW = 4


def test_the_old_teardown_destroyed_nothing(application: QApplication) -> None:
    """The defect itself, kept as a test so its shape cannot be forgotten."""
    before = len(application.allWidgets())
    for _ in range(A_FEW):
        widget = QWidget()
        widget.show()
        widget.close()
        widget.deleteLater()
        QApplication.processEvents()

    assert len(application.allWidgets()) > before

    destroy_all_widgets(application)

    assert application.topLevelWidgets() == []


def test_the_teardown_leaves_nothing_alive(application: QApplication) -> None:
    parent = QWidget()
    QWidget(parent)
    parent.show()

    assert application.topLevelWidgets() != []

    destroy_all_widgets(application)

    assert application.topLevelWidgets() == []
    assert application.allWidgets() == []
