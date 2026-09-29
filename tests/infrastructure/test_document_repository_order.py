"""A folder's declared order reaches the tree; its record never becomes a row."""

from __future__ import annotations

import json
from pathlib import Path

from plainsight.__main__ import build_readers
from plainsight.infrastructure.collection_manifest import MANIFEST_NAME
from plainsight.infrastructure.document_repository import FileSystemDocumentRepository

NEWEST_FIRST = ("2026-03-01_v3.md", "2026-02-01_v2.md", "2026-01-01_v1.md")


def a_collection(root: Path, record: str | None) -> Path:
    root.mkdir()
    for name in (*NEWEST_FIRST, "my-notes.md"):
        (root / name).write_text(f"# {name}\n\nBody.\n", encoding="utf-8")
    if record is not None:
        (root / MANIFEST_NAME).write_text(record, encoding="utf-8")
    return root


def listed(root: Path) -> list[str]:
    folder = FileSystemDocumentRepository(build_readers()).read_folder(str(root))
    assert folder is not None
    return [document.name for document in folder.documents]


def test_a_declared_order_lists_newest_first_then_everything_else(
    tmp_path: Path,
) -> None:
    record = json.dumps({"documents": [{"file": name} for name in NEWEST_FIRST]})

    assert listed(a_collection(tmp_path / "releases", record)) == [
        *NEWEST_FIRST,
        "my-notes.md",
    ]


def test_without_a_record_the_folder_lists_by_name(tmp_path: Path) -> None:
    assert listed(a_collection(tmp_path / "releases", None)) == sorted(
        [*NEWEST_FIRST, "my-notes.md"], key=str.casefold
    )


def test_an_unreadable_record_costs_only_its_order(tmp_path: Path) -> None:
    root = a_collection(tmp_path / "releases", None)
    (root / MANIFEST_NAME).write_bytes(b"\xff\xfe")

    assert listed(root) == sorted([*NEWEST_FIRST, "my-notes.md"], key=str.casefold)
