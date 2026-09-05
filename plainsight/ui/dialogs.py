"""The modal things the window puts up: the choosers and the licences.

Gathered out of the window because they are one concern rather than part of
its own state: each takes a parent, asks the desktop something and answers.
The window is left saying what to do with the answer.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QFileDialog, QWidget

from ..application.ports import AssetLocator
from ..domain.document import readable_suffixes
from .about_dialog import AboutDialog
from .guide_dialog import GuideDialog
from .licence_dialog import LicenceDialog
from .theme import Palette

FOLDER_PROMPT = "Choose the folder your documents live in"
FILE_PROMPT = "Open a document"
EDITOR_PROMPT = "Choose the editor to open a document in"
READABLE_FILTER_NAME = "Documents"
ALL_FILES_FILTER = "All files (*)"

UI_LICENCE_TITLE = "User interface licence (LGPL-3.0)"
MODEL_LICENCE_TITLE = "Model licence (GPL-3.0)"
UI_LICENCE_FILE = "LICENSE-LGPL-3.0.txt"
MODEL_LICENCE_FILE = "LICENSE-GPL-3.0.txt"
FALLBACK_LICENCE_FILE = "LICENSE"


def readable_filter() -> str:
    """The chooser's filter, built from the kinds this application reads.

    Derived rather than written out, so a kind added to the enumeration is
    offered by the dialogue without anyone remembering to come back here.
    """
    patterns = " ".join(f"*{suffix}" for suffix in readable_suffixes())
    return f"{READABLE_FILTER_NAME} ({patterns});;{ALL_FILES_FILTER}"


def ask_for_folder(parent: QWidget, start: str) -> str:
    """A folder of documents; empty when the reader closed the chooser.

    ``start`` is where the dialogue opens, which reads nothing by being
    offered: the reader is standing in front of it and nothing is taken until
    they take it.
    """
    return QFileDialog.getExistingDirectory(parent, FOLDER_PROMPT, start)


def ask_for_document(parent: QWidget, start: str) -> str:
    """One document; empty when the reader closed the chooser."""
    chosen, _filter = QFileDialog.getOpenFileName(
        parent, FILE_PROMPT, start, readable_filter()
    )
    return chosen


def ask_for_editor(parent: QWidget) -> str:
    """An editor executable; empty when the reader closed the chooser."""
    chosen, _filter = QFileDialog.getOpenFileName(parent, EDITOR_PROMPT)
    return chosen


def find_licence(file_name: str) -> Path | None:
    """A licence file at the repository root; the single LICENSE as fallback."""
    root = Path(__file__).resolve().parent.parent.parent
    for candidate in (root / file_name, root / FALLBACK_LICENCE_FILE):
        if candidate.is_file():
            return candidate
    return None


def _show_licence(parent: QWidget, title: str, file_name: str) -> None:
    """Open one licence, destroyed as it closes rather than left alive."""
    LicenceDialog(title, find_licence(file_name), parent).exec()


def show_ui_licence(parent: QWidget) -> None:
    """Open the user interface licence."""
    _show_licence(parent, UI_LICENCE_TITLE, UI_LICENCE_FILE)


def show_model_licence(parent: QWidget) -> None:
    """Open the model licence."""
    _show_licence(parent, MODEL_LICENCE_TITLE, MODEL_LICENCE_FILE)


def show_about(parent: QWidget, palette: Palette, assets: AssetLocator) -> None:
    """Open the About dialog."""
    AboutDialog(palette, assets, parent).exec()


def show_guide(parent: QWidget, palette: Palette, assets: AssetLocator) -> None:
    """Open the guide."""
    GuideDialog(palette, assets, parent).exec()
