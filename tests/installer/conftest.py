"""One real QApplication for the setup program's own tests."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from PySide6.QtWidgets import QApplication

from tests.qt_teardown import destroy_all_widgets


@pytest.fixture(scope="session")
def application() -> Iterator[QApplication]:
    existing = QApplication.instance()
    yield existing if existing is not None else QApplication([])


@pytest.fixture(autouse=True)
def close_orphans(application: QApplication) -> Iterator[None]:
    """Nothing left ALIVE between tests, not merely nothing on screen.

    These widgets outlived this suite entirely and were still in the
    application when the first window of the user interface suite repainted
    the application stylesheet, which is where the run died. See
    `tests/qt_teardown.py` for what the old teardown actually did.
    """
    yield
    destroy_all_widgets(application)
