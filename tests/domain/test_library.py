"""The tree: what a folder holds, in what order, then what the library sees."""

from __future__ import annotations

from plainsight.domain.document import Document, DocumentKind
from plainsight.domain.library import Folder, Library


def a_document(name: str, path: str = "") -> Document:
    """A readable Markdown document with a name and a path of its own."""
    return Document(
        name=name,
        path=path or f"/root/{name}",
        kind=DocumentKind.MARKDOWN,
    )


def test_a_folder_orders_its_documents_case_insensitively() -> None:
    folder = Folder.of(
        "root",
        "/root",
        documents=[a_document("beta.md"), a_document("Alpha.md")],
    )

    assert [one.name for one in folder.documents] == ["Alpha.md", "beta.md"]


def test_a_folder_orders_its_subfolders_case_insensitively() -> None:
    folder = Folder.of(
        "root",
        "/root",
        folders=[
            Folder.of("zebra", "/root/zebra"),
            Folder.of("Aardvark", "/root/Aardvark"),
        ],
    )

    assert [one.name for one in folder.folders] == ["Aardvark", "zebra"]


def test_a_folder_orders_by_its_own_name_case_insensitively() -> None:
    assert Folder.of("Prose", "/root/Prose").sort_key == "prose"


def test_a_folder_counts_every_document_beneath_it_however_deep() -> None:
    deep = Folder.of("deep", "/root/one/deep", documents=[a_document("three.md")])
    one = Folder.of(
        "one", "/root/one", folders=[deep], documents=[a_document("two.md")]
    )
    root = Folder.of("root", "/root", folders=[one], documents=[a_document("one.md")])

    assert root.document_count == 3


def test_a_folder_leading_to_no_document_is_empty() -> None:
    """Even when it has folders of its own, so long as none of them holds one."""
    inner = Folder.of("inner", "/root/inner")
    root = Folder.of("root", "/root", folders=[inner])

    assert inner.is_empty
    assert root.is_empty


def test_a_folder_walks_its_subfolders_before_its_own_documents() -> None:
    """Folders are drawn above documents, so walking follows the drawn order."""
    inner = Folder.of("inner", "/root/inner", documents=[a_document("inner.md")])
    root = Folder.of(
        "root", "/root", folders=[inner], documents=[a_document("outer.md")]
    )

    assert [one.name for one in root] == ["inner.md", "outer.md"]


def test_an_empty_library_holds_nothing() -> None:
    assert Library().is_empty
    assert Library().document_count == 0


def test_a_library_of_empty_roots_is_still_empty() -> None:
    """A root that leads nowhere must not read as content that is simply hidden."""
    assert Library((Folder.of("root", "/root"),)).is_empty


def test_a_library_counts_and_walks_every_root_in_order() -> None:
    first = Folder.of(
        "skills", "/skills", documents=[a_document("a.md", "/skills/a.md")]
    )
    second = Folder.of(
        "plugins", "/plugins", documents=[a_document("b.md", "/plugins/b.md")]
    )
    library = Library((first, second))

    assert not library.is_empty
    assert library.document_count == 2
    assert [one.name for one in library] == ["a.md", "b.md"]


def test_a_library_finds_a_document_by_the_path_it_was_read_from() -> None:
    """The path is the identity that survives a re-read, not the display name."""
    wanted = a_document("a.md", "/skills/a.md")
    library = Library((Folder.of("skills", "/skills", documents=[wanted]),))

    assert library.by_path("/skills/a.md") == wanted


def test_a_path_the_library_never_read_finds_nothing() -> None:
    library = Library((Folder.of("skills", "/skills", documents=[a_document("a.md")]),))

    assert library.by_path("/elsewhere/a.md") is None
