"""Reading a real tree: what becomes a folder, what becomes a document."""

from __future__ import annotations

from pathlib import Path

from plainsight.__main__ import build_readers
from plainsight.domain.document import DocumentKind
from plainsight.domain.library import Folder
from plainsight.infrastructure.document_reader import (
    EMPTY_MARKDOWN_TEXT,
    EMPTY_TEXT,
    UNREADABLE_TEXT,
)
from plainsight.infrastructure.document_repository import (
    UNKNOWN_KIND,
    FileSystemDocumentRepository,
)

A_SKILL = "---\nname: prose\ndescription: writing\n---\n\n# Prose\n\nBody.\n"


def a_repository() -> FileSystemDocumentRepository:
    """The repository as the composition root builds it, readers and all."""
    return FileSystemDocumentRepository(build_readers())


def read(root: Path) -> Folder | None:
    """The tree beneath this directory, as the application would read it."""
    return a_repository().read_folder(str(root))


def body(path: Path) -> str:
    """The text of one document, fetched the way opening it fetches it."""
    return a_repository().read_body(str(path)).text


def names(folder: Folder) -> list[str]:
    """Every document beneath a folder, in the order they are drawn."""
    return [document.name for document in folder]


def test_a_root_that_is_not_there_reads_as_nothing(tmp_path: Path) -> None:
    assert read(tmp_path / "absent") is None


def test_a_root_holding_nothing_we_read_reads_as_nothing(tmp_path: Path) -> None:
    """Not an empty folder: nothing at all, so no root is shown over no content."""
    (tmp_path / "photo.png").write_bytes(b"\x89PNG")

    assert read(tmp_path) is None


def test_a_markdown_file_is_a_document(tmp_path: Path) -> None:
    (tmp_path / "notes.md").write_text("Body.", encoding="utf-8")

    folder = read(tmp_path)

    assert names(folder) == ["notes.md"]
    assert folder.documents[0].kind is DocumentKind.MARKDOWN


def test_a_text_file_is_a_document_too(tmp_path: Path) -> None:
    """The generalisation that made this a document viewer rather than a skills one."""
    (tmp_path / "shopping.txt").write_text("Milk", encoding="utf-8")

    folder = read(tmp_path)

    assert names(folder) == ["shopping.txt"]
    assert folder.documents[0].kind is DocumentKind.PLAIN_TEXT


def test_an_html_file_is_a_document_under_either_suffix(tmp_path: Path) -> None:
    """A reader who saved a page as ``.htm`` asked for the same thing."""
    (tmp_path / "guide.html").write_text("<p>One</p>", encoding="utf-8")
    (tmp_path / "manual.htm").write_text("<p>Two</p>", encoding="utf-8")

    folder = read(tmp_path)

    assert names(folder) == ["guide.html", "manual.htm"]
    for document in folder:
        assert document.kind is DocumentKind.HTML


def test_an_html_file_keeps_its_markup_rather_than_declaring_fields(
    tmp_path: Path,
) -> None:
    """A leading fence in a page is markup, never a block of fields."""
    (tmp_path / "page.html").write_text("---\n<p>Body.</p>\n", encoding="utf-8")

    document = read(tmp_path).documents[0]

    assert document.declared_fields == ()
    assert body(tmp_path / "page.html") == "---\n<p>Body.</p>\n"


def test_anything_else_is_not_a_document(tmp_path: Path) -> None:
    (tmp_path / "notes.md").write_text("Body.", encoding="utf-8")
    (tmp_path / "photo.png").write_bytes(b"\x89PNG")
    (tmp_path / "script.py").write_text("pass", encoding="utf-8")

    assert names(read(tmp_path)) == ["notes.md"]


def test_a_folder_of_documents_reads_as_a_folder(tmp_path: Path) -> None:
    """A skill is exactly this shape: a directory holding its files together."""
    skill = tmp_path / "prose"
    skill.mkdir()
    (skill / "SKILL.md").write_text(A_SKILL, encoding="utf-8")
    (skill / "sweep.md").write_text("Sweep.", encoding="utf-8")

    root = read(tmp_path)

    assert [one.name for one in root.folders] == ["prose"]
    assert names(root) == ["SKILL.md", "sweep.md"]


def test_a_document_is_found_however_deep_it_sits(tmp_path: Path) -> None:
    """A rule rather than a path template, so a layout change cannot outrun it."""
    deep = tmp_path / "market" / "plugin" / "skills" / "hookify"
    deep.mkdir(parents=True)
    (deep / "SKILL.md").write_text(A_SKILL, encoding="utf-8")

    assert names(read(tmp_path)) == ["SKILL.md"]


def test_a_branch_leading_to_no_document_is_not_reported(tmp_path: Path) -> None:
    """Every branch the reader can open leads somewhere."""
    (tmp_path / "notes.md").write_text("Body.", encoding="utf-8")
    (tmp_path / "images").mkdir()
    (tmp_path / "images" / "photo.png").write_bytes(b"\x89PNG")

    assert [one.name for one in read(tmp_path).folders] == []


def test_hidden_and_cache_directories_are_passed_over(tmp_path: Path) -> None:
    for hidden in (".git", "__pycache__"):
        directory = tmp_path / hidden
        directory.mkdir()
        (directory / "notes.md").write_text("Body.", encoding="utf-8")
    (tmp_path / "kept.md").write_text("Body.", encoding="utf-8")

    assert names(read(tmp_path)) == ["kept.md"]


def test_a_hidden_directory_is_passed_over_at_any_depth(tmp_path: Path) -> None:
    buried = tmp_path / "plugin" / ".cache"
    buried.mkdir(parents=True)
    (buried / "notes.md").write_text("Body.", encoding="utf-8")
    (tmp_path / "kept.md").write_text("Body.", encoding="utf-8")

    assert names(read(tmp_path)) == ["kept.md"]


def test_folders_come_before_documents_and_each_is_ordered_by_name(
    tmp_path: Path,
) -> None:
    for name in ("beta.md", "Alpha.md"):
        (tmp_path / name).write_text("Body.", encoding="utf-8")
    for folder in ("zebra", "Aardvark"):
        made = tmp_path / folder
        made.mkdir()
        (made / "inner.md").write_text("Body.", encoding="utf-8")

    root = read(tmp_path)

    assert [one.name for one in root.folders] == ["Aardvark", "zebra"]
    assert [one.name for one in root.documents] == ["Alpha.md", "beta.md"]


def test_a_markdown_document_gives_up_what_it_declares(tmp_path: Path) -> None:
    (tmp_path / "SKILL.md").write_text(A_SKILL, encoding="utf-8")

    document = read(tmp_path).documents[0]

    assert document.name == "SKILL.md"
    assert document.declared_name == "prose"
    assert document.title == "prose"
    assert document.description == "writing"
    assert body(tmp_path / "SKILL.md").startswith("# Prose")


def test_a_text_document_declares_nothing_whatever_it_opens_with(
    tmp_path: Path,
) -> None:
    """Three hyphens in a text file are three hyphens, not a block of fields."""
    (tmp_path / "notes.txt").write_text("---\nname: not a field\n---\nBody.\n", "utf-8")

    document = read(tmp_path).documents[0]

    assert document.declared_fields == ()
    assert document.declared_name == ""
    assert document.title == "notes.txt"
    assert body(tmp_path / "notes.txt").startswith("---")


def test_a_listed_document_carries_a_fingerprint_of_the_file(tmp_path: Path) -> None:
    """It stands in for the body in deciding whether a document has changed."""
    (tmp_path / "notes.md").write_text("Body.", encoding="utf-8")

    assert read(tmp_path).documents[0].fingerprint


def test_the_same_file_edited_fingerprints_differently(tmp_path: Path) -> None:
    """Without this the pane would leave a stale rendering exactly where it was."""
    written = tmp_path / "notes.md"
    written.write_text("Body.", encoding="utf-8")
    before = read(tmp_path).documents[0]

    written.write_text("A longer body than before.", encoding="utf-8")
    after = read(tmp_path).documents[0]

    assert before.fingerprint != after.fingerprint
    assert before != after


def test_reading_the_same_unchanged_file_twice_gives_the_same_document(
    tmp_path: Path,
) -> None:
    """The other half: an unchanged file must compare equal to itself."""
    (tmp_path / "notes.md").write_text("Body.", encoding="utf-8")

    assert read(tmp_path).documents[0] == read(tmp_path).documents[0]


def test_the_body_of_a_file_that_is_not_a_document_says_why(tmp_path: Path) -> None:
    """No reader claims it, so the repository answers rather than looking one up."""
    (tmp_path / "photo.png").write_bytes(b"\x89PNG")

    asked = a_repository().read_body(str(tmp_path / "photo.png"))

    assert asked.text == ""
    assert asked.failure == UNKNOWN_KIND


def test_the_body_of_a_file_that_is_not_there_is_empty(tmp_path: Path) -> None:
    """Between being listed and being opened, a file can go away."""
    assert body(tmp_path / "absent.md") == ""


def test_the_body_of_a_file_that_is_not_text_is_empty(tmp_path: Path) -> None:
    (tmp_path / "broken.md").write_bytes(b"\xff\xfe\x00binary")

    assert body(tmp_path / "broken.md") == ""


def test_a_body_arrives_without_the_fields_it_declared(tmp_path: Path) -> None:
    """The header shows those; repeating them in the body would show them twice."""
    (tmp_path / "SKILL.md").write_text(A_SKILL, encoding="utf-8")

    text = body(tmp_path / "SKILL.md")

    assert text.startswith("# Prose")
    assert "description: writing" not in text


def test_a_file_that_is_not_text_is_still_listed(tmp_path: Path) -> None:
    """The reader neither caused this nor can fix it from here, so it is shown."""
    (tmp_path / "broken.md").write_bytes(b"\xff\xfe\x00binary")

    document = read(tmp_path).documents[0]

    assert not document.is_readable
    assert document.failure == UNREADABLE_TEXT


def test_an_empty_markdown_file_reports_that_rather_than_vanishing(
    tmp_path: Path,
) -> None:
    (tmp_path / "SKILL.md").write_text("---\nname: hollow\n---\n\n", encoding="utf-8")

    document = read(tmp_path).documents[0]

    assert document.failure == EMPTY_MARKDOWN_TEXT


def test_an_empty_text_file_reports_the_plainer_reason(tmp_path: Path) -> None:
    """It has no frontmatter to be empty beneath, so it must not say it has."""
    (tmp_path / "notes.txt").write_text("   \n", encoding="utf-8")

    document = read(tmp_path).documents[0]

    assert document.failure == EMPTY_TEXT


def test_a_directory_that_cannot_be_listed_costs_only_itself(tmp_path: Path) -> None:
    """One unreadable folder must not cost the reader the whole tree."""
    (tmp_path / "kept.md").write_text("Body.", encoding="utf-8")
    blocked = tmp_path / "blocked"
    blocked.mkdir()
    (blocked / "inner.md").write_text("Body.", encoding="utf-8")

    original = Path.iterdir

    def refuse(self: Path):
        if self.name == "blocked":
            raise PermissionError(self.name)
        return original(self)

    Path.iterdir = refuse  # type: ignore[method-assign]
    try:
        assert names(read(tmp_path)) == ["kept.md"]
    finally:
        Path.iterdir = original  # type: ignore[method-assign]


def test_a_file_that_disappears_between_listing_and_reading_is_reported(
    tmp_path: Path,
) -> None:
    """Read as a failure rather than raised: the tree was true a moment ago."""
    (tmp_path / "notes.md").write_text("Body.", encoding="utf-8")

    original = Path.read_text

    def refuse(self: Path, *args: object, **kwargs: object) -> str:
        raise OSError(self.name)

    Path.read_text = refuse  # type: ignore[method-assign]
    try:
        document = read(tmp_path).documents[0]
    finally:
        Path.read_text = original  # type: ignore[method-assign]

    assert not document.is_readable
