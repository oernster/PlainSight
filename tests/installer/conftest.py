"""One real QApplication for the setup program's own tests."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from PySide6.QtWidgets import QApplication, QWidget


@pytest.fixture(scope="session")
def application() -> Iterator[QApplication]:
    existing = QApplication.instance()
    yield existing if existing is not None else QApplication([])


@pytest.fixture(autouse=True)
def close_orphans(application: QApplication) -> Iterator[None]:
    """Nothing left on screen between tests."""
    yield
    for widget in list(application.topLevelWidgets()):
        if isinstance(widget, QWidget):
            widget.close()
