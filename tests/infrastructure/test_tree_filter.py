"""The tree filter at the walk: environment folders and empty documents.

A ``venv`` or a ``node_modules`` holds somebody else's code, often thousands of
files of it, some of which are documents by suffix alone. An empty document is
a row that opens onto nothing. While the filter is on neither is listed; while
it is off both are. The dot and cache rules stay as they were either way.
"""

from __future__ import annotations

from pathlib import Path

import docx

from plainsight.__main__ import build_readers
from plainsight.domain.library import Folder
from plainsight.infrastructure.document_repository import FileSystemDocumentRepository

from .pdf_fixtures import a_pdf_with_no_text

A_SCRIPT_ONLY_PAGE = (
    "<!doctype html><html><head><title>API</title></head>"
    '<body><div id="ui"></div><script src="bundle.js"></script></body></html>'
)


def a_repository() -> FileSystemDocumentRepository:
    return FileSystemDocumentRepository(build_readers())


def read(root: Path, filter_tree: bool) -> Folder | None:
    """The tree beneath this directory, filtered or not."""
    return a_repository().read_folder(str(root), filter_tree=filter_tree)


def names(folder: Folder) -> list[str]:
    """Every document beneath a folder, in the order they are drawn."""
    return [document.name for document in folder]


def a_document_in(directory: Path, name: str = "README.md") -> None:
    """One Markdown document with a body, inside this directory."""
    directory.mkdir(parents=True, exist_ok=True)
    (directory / name).write_text("Body.", encoding="utf-8")


def empty_documents_in(directory: Path) -> None:
    """One empty document of every kind that can be judged empty at listing."""
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "hollow.md").write_text("---\nname: hollow\n---\n", encoding="utf-8")
    (directory / "blank.txt").write_text("  \n\n", encoding="utf-8")
    (directory / "swagger_ui.html").write_text(A_SCRIPT_ONLY_PAGE, encoding="utf-8")
    docx.Document().save(str(directory / "nothing.docx"))


def test_environment_folders_are_passed_over_by_default(tmp_path: Path) -> None:
    """Named literally rather than looped over the constant.

    Looped over it, an emptied constant made no folders at all and this passed;
    measured by planting exactly that.
    """
    a_document_in(tmp_path / "venv", "venv.md")
    a_document_in(tmp_path / "node_modules", "node_modules.md")
    a_document_in(tmp_path, "kept.md")

    assert names(a_repository().read_folder(str(tmp_path))) == ["kept.md"]


def test_environment_folders_are_read_while_the_filter_is_off(tmp_path: Path) -> None:
    a_document_in(tmp_path / "venv", "venv.md")
    a_document_in(tmp_path / "node_modules", "node_modules.md")
    a_document_in(tmp_path, "kept.md")

    root = read(tmp_path, filter_tree=False)

    assert [one.name for one in root.folders] == ["node_modules", "venv"]
    assert names(root) == ["node_modules.md", "venv.md", "kept.md"]


def test_an_environment_folder_is_passed_over_at_any_depth(tmp_path: Path) -> None:
    a_document_in(tmp_path / "app" / "web" / "node_modules" / "left-pad")
    a_document_in(tmp_path / "app", "kept.md")

    assert names(read(tmp_path, filter_tree=True)) == ["kept.md"]


def test_a_folder_leading_only_into_an_environment_folder_is_not_reported(
    tmp_path: Path,
) -> None:
    """With the environment filtered that branch leads nowhere, so it is not shown."""
    a_document_in(tmp_path / "tool" / "venv" / "lib" / "package")
    a_document_in(tmp_path, "kept.md")

    root = read(tmp_path, filter_tree=True)

    assert [one.name for one in root.folders] == []
    assert names(root) == ["kept.md"]


def test_the_same_folder_is_reported_once_the_filter_is_off(tmp_path: Path) -> None:
    a_document_in(tmp_path / "tool" / "venv" / "lib" / "package")
    a_document_in(tmp_path, "kept.md")

    root = read(tmp_path, filter_tree=False)

    assert [one.name for one in root.folders] == ["tool"]
    assert names(root) == ["README.md", "kept.md"]


def test_a_root_holding_documents_only_inside_an_environment_is_nothing(
    tmp_path: Path,
) -> None:
    a_document_in(tmp_path / "node_modules" / "left-pad")

    assert read(tmp_path, filter_tree=True) is None


def test_hidden_and_cache_folders_stay_hidden_while_the_filter_is_off(
    tmp_path: Path,
) -> None:
    """``.git`` and ``.venv`` go by their dot and ``__pycache__`` by its name."""
    for hidden in (".git", ".venv", "__pycache__"):
        a_document_in(tmp_path / hidden)
    a_document_in(tmp_path, "kept.md")

    assert names(read(tmp_path, filter_tree=False)) == ["kept.md"]


def test_a_name_merely_containing_an_environment_name_is_read(tmp_path: Path) -> None:
    """Named exactly: a folder called ``venv-notes`` is somebody's notes."""
    a_document_in(tmp_path / "venv-notes")
    a_document_in(tmp_path / "my_node_modules")

    root = read(tmp_path, filter_tree=True)

    assert [one.name for one in root.folders] == ["my_node_modules", "venv-notes"]


def test_empty_documents_are_left_out_while_the_filter_is_on(tmp_path: Path) -> None:
    """Every kind that can be judged at listing: text, Markdown, HTML and Word."""
    empty_documents_in(tmp_path)
    a_document_in(tmp_path, "kept.md")

    assert names(read(tmp_path, filter_tree=True)) == ["kept.md"]


def test_empty_documents_are_listed_while_the_filter_is_off(tmp_path: Path) -> None:
    empty_documents_in(tmp_path)
    a_document_in(tmp_path, "kept.md")

    assert names(read(tmp_path, filter_tree=False)) == [
        "blank.txt",
        "hollow.md",
        "kept.md",
        "nothing.docx",
        "swagger_ui.html",
    ]


def test_a_folder_holding_only_empty_documents_is_not_reported(tmp_path: Path) -> None:
    empty_documents_in(tmp_path / "templates")
    a_document_in(tmp_path, "kept.md")

    root = read(tmp_path, filter_tree=True)

    assert [one.name for one in root.folders] == []
    assert names(root) == ["kept.md"]


def test_a_root_holding_only_empty_documents_is_nothing(tmp_path: Path) -> None:
    empty_documents_in(tmp_path)

    assert read(tmp_path, filter_tree=True) is None


def test_a_document_that_cannot_be_read_is_still_listed(tmp_path: Path) -> None:
    """Unreadable is not empty: the row says why, which is worth seeing."""
    (tmp_path / "broken.md").write_bytes(b"\xff\xfe\x00binary")

    assert names(read(tmp_path, filter_tree=True)) == ["broken.md"]


def test_a_pdf_is_not_judged_empty_at_listing(tmp_path: Path) -> None:
    """Knowing needs its pages extracted, which a listing never does."""
    (tmp_path / "scan.pdf").write_bytes(a_pdf_with_no_text())

    assert names(read(tmp_path, filter_tree=True)) == ["scan.pdf"]


def test_an_empty_document_opened_on_its_own_is_still_read(tmp_path: Path) -> None:
    """Opening one file asked for that file, so nothing filters it away."""
    (tmp_path / "blank.txt").write_text("\n", encoding="utf-8")

    document = a_repository().read_document(str(tmp_path / "blank.txt"))

    assert document is not None
    assert document.holds_no_text
