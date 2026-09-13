"""Environment folders: passed over unless the reader asks to see them.

A ``venv`` or a ``node_modules`` holds somebody else's code, often thousands of
files of it, some of which are documents by suffix alone. They are hidden by
default and read only when asked for; the dot and cache rules stay as they
were whatever is asked.
"""

from __future__ import annotations

from pathlib import Path

from plainsight.__main__ import build_readers
from plainsight.domain.library import Folder
from plainsight.infrastructure.document_repository import FileSystemDocumentRepository


def read(root: Path, include_environment_folders: bool) -> Folder | None:
    """The tree beneath this directory, environment folders shown or not."""
    return FileSystemDocumentRepository(build_readers()).read_folder(
        str(root), include_environment_folders=include_environment_folders
    )


def names(folder: Folder) -> list[str]:
    """Every document beneath a folder, in the order they are drawn."""
    return [document.name for document in folder]


def a_document_in(directory: Path, name: str = "README.md") -> None:
    """One Markdown document inside this directory, made along with it."""
    directory.mkdir(parents=True, exist_ok=True)
    (directory / name).write_text("Body.", encoding="utf-8")


def test_environment_folders_are_passed_over_by_default(tmp_path: Path) -> None:
    """Named literally rather than looped over the constant.

    Looped over it, an emptied constant made no folders at all and this passed;
    measured by planting exactly that.
    """
    a_document_in(tmp_path / "venv", "venv.md")
    a_document_in(tmp_path / "node_modules", "node_modules.md")
    a_document_in(tmp_path, "kept.md")

    assert names(
        FileSystemDocumentRepository(build_readers()).read_folder(str(tmp_path))
    ) == ["kept.md"]


def test_environment_folders_are_read_when_asked_for(tmp_path: Path) -> None:
    a_document_in(tmp_path / "venv", "venv.md")
    a_document_in(tmp_path / "node_modules", "node_modules.md")
    a_document_in(tmp_path, "kept.md")

    root = read(tmp_path, include_environment_folders=True)

    assert [one.name for one in root.folders] == ["node_modules", "venv"]
    assert names(root) == ["node_modules.md", "venv.md", "kept.md"]


def test_an_environment_folder_is_passed_over_at_any_depth(tmp_path: Path) -> None:
    a_document_in(tmp_path / "app" / "web" / "node_modules" / "left-pad")
    a_document_in(tmp_path / "app", "kept.md")

    assert names(read(tmp_path, include_environment_folders=False)) == ["kept.md"]


def test_a_folder_leading_only_into_an_environment_folder_is_not_reported(
    tmp_path: Path,
) -> None:
    """With the environment hidden that branch leads nowhere, so it is not shown."""
    a_document_in(tmp_path / "tool" / "venv" / "lib" / "package")
    a_document_in(tmp_path, "kept.md")

    root = read(tmp_path, include_environment_folders=False)

    assert [one.name for one in root.folders] == []
    assert names(root) == ["kept.md"]


def test_the_same_folder_is_reported_once_environment_folders_are_shown(
    tmp_path: Path,
) -> None:
    a_document_in(tmp_path / "tool" / "venv" / "lib" / "package")
    a_document_in(tmp_path, "kept.md")

    root = read(tmp_path, include_environment_folders=True)

    assert [one.name for one in root.folders] == ["tool"]
    assert names(root) == ["README.md", "kept.md"]


def test_a_root_holding_documents_only_inside_an_environment_is_nothing(
    tmp_path: Path,
) -> None:
    a_document_in(tmp_path / "node_modules" / "left-pad")

    assert read(tmp_path, include_environment_folders=False) is None


def test_hidden_and_cache_folders_stay_hidden_when_environments_are_shown(
    tmp_path: Path,
) -> None:
    """``.venv`` goes by its dot and ``__pycache__`` by its name, always."""
    for hidden in (".venv", "__pycache__"):
        a_document_in(tmp_path / hidden)
    a_document_in(tmp_path, "kept.md")

    assert names(read(tmp_path, include_environment_folders=True)) == ["kept.md"]


def test_a_name_merely_containing_an_environment_name_is_read(tmp_path: Path) -> None:
    """Named exactly: a folder called ``venv-notes`` is somebody's notes."""
    a_document_in(tmp_path / "venv-notes")
    a_document_in(tmp_path / "my_node_modules")

    root = read(tmp_path, include_environment_folders=False)

    assert [one.name for one in root.folders] == ["my_node_modules", "venv-notes"]
