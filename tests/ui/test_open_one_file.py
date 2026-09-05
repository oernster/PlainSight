"""Opening one document on its own, then having it stay open.

The library is re-read every time the window is activated, which is the whole
freshness model. Closing the chooser is what activates the window, so a re-read
that always went back to the chosen folder threw the opened file away in the
same moment the reader opened it. That is what these tests hold.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QEvent
from PySide6.QtWidgets import QApplication

from plainsight.ui import main_window
from plainsight.ui.main_window import MainWindow

A_NOTE = "# Notes\n\nA distinctive sentence.\n"
NOTHING = 0


def elsewhere(tmp_path: Path, name: str = "notes.md", text: str = A_NOTE) -> Path:
    """A document that is not beneath the folder the reader chose."""
    directory = tmp_path / "elsewhere"
    directory.mkdir(exist_ok=True)
    written = directory / name
    written.write_text(text, encoding="utf-8")
    return written


def choosing(target: Path) -> None:
    """Stand in for the chooser, which a test cannot drive."""
    main_window.dialogs.ask_for_document = lambda parent, start: str(target)


def activate(window: MainWindow) -> None:
    """What closing a modal chooser does to the window underneath it."""
    window.changeEvent(QEvent(QEvent.Type.ActivationChange))
    QApplication.processEvents()


def rows(window: MainWindow) -> list[str]:
    return [item.text(0) for item in window.library_tree.document_items()]


def test_opening_one_file_shows_it(window: MainWindow, tmp_path: Path) -> None:
    target = elsewhere(tmp_path)
    choosing(target)

    window.open_file()
    QApplication.processEvents()

    assert rows(window) == ["notes.md"]
    assert "A distinctive sentence." in window.document_view.toPlainText()


def test_an_opened_file_survives_the_window_being_activated(
    window: MainWindow, tmp_path: Path
) -> None:
    """The defect this file exists for, reported as the file not opening at all.

    It did open. Activation then read the chosen folder again and replaced it,
    which happens the instant the chooser closes, so the reader never saw it.
    """
    target = elsewhere(tmp_path)
    choosing(target)
    window.open_file()
    QApplication.processEvents()

    activate(window)

    assert rows(window) == ["notes.md"]
    assert "A distinctive sentence." in window.document_view.toPlainText()


def test_an_opened_file_is_re_read_rather_than_merely_kept(
    window: MainWindow, tmp_path: Path
) -> None:
    """The freshness promise holds for one file exactly as for a folder."""
    target = elsewhere(tmp_path)
    choosing(target)
    window.open_file()
    QApplication.processEvents()

    target.write_text("# Notes\n\nEdited on disk since.\n", encoding="utf-8")
    activate(window)

    assert "Edited on disk since." in window.document_view.toPlainText()


def test_an_opened_file_that_goes_away_falls_back_to_the_folder(
    window: MainWindow, tmp_path: Path
) -> None:
    """Better the chosen folder than a tree describing nothing at all."""
    target = elsewhere(tmp_path)
    choosing(target)
    window.open_file()
    QApplication.processEvents()

    target.unlink()
    activate(window)

    assert "notes.md" not in rows(window)
    assert len(rows(window)) > NOTHING


def test_choosing_a_folder_afterwards_leaves_the_opened_file_behind(
    window: MainWindow, tmp_path: Path
) -> None:
    """Browsing to a folder is the reader saying they want the folder."""
    target = elsewhere(tmp_path)
    choosing(target)
    window.open_file()
    QApplication.processEvents()
    chosen = tmp_path / "skills"
    main_window.dialogs.ask_for_folder = lambda parent, start: str(chosen)

    window.choose_folder()
    QApplication.processEvents()
    activate(window)

    assert "notes.md" not in rows(window)
    assert "SKILL.md" in rows(window)
