"""Hand-written stand-ins for the application's ports.

Written rather than generated, so each one records exactly what a test needs to
assert about it and nothing more.
"""

from __future__ import annotations

from plainsight.domain.document import Document, DocumentBody, DocumentKind
from plainsight.domain.library import Folder
from plainsight.domain.settings import EditorChoice, Settings


def a_document(name: str = "SKILL.md", folder: str = "/skills/prose") -> Document:
    """A readable document, for tests that need one rather than describe one."""
    return Document(
        name=name,
        path=f"{folder}/{name}",
        kind=DocumentKind.MARKDOWN,
        fingerprint="4:1",
    )


def a_folder(name: str = "skills", path: str = "/skills", *names: str) -> Folder:
    """A folder holding one document per name given, else a single default one."""
    wanted = names or ("SKILL.md",)
    return Folder.of(name, path, documents=[a_document(one, path) for one in wanted])


class FakeRepository:
    """Reports a fixed folder per root and records every root it was asked for.

    ``roots_read`` and ``files_read`` are kept apart because the difference
    matters: reading one file must list no directory, which can only be said
    by watching the two calls separately. ``bodies_read`` is a third for the
    same reason: a body is fetched when a document is opened, so a listing
    that read one would be doing the work this seam exists to avoid.
    """

    def __init__(
        self,
        folders: dict[str, Folder | None] | None = None,
        documents: dict[str, Document | None] | None = None,
        bodies: dict[str, str] | None = None,
    ) -> None:
        self.folders: dict[str, Folder | None] = dict(folders or {})
        self.documents: dict[str, Document | None] = dict(documents or {})
        self.bodies: dict[str, str] = dict(bodies or {})
        self.roots_read: list[str] = []
        self.files_read: list[str] = []
        self.bodies_read: list[str] = []

    def read_folder(self, root: str) -> Folder | None:
        self.roots_read.append(root)
        return self.folders.get(root)

    def read_document(self, path: str) -> Document | None:
        self.files_read.append(path)
        return self.documents.get(path)

    def read_body(self, path: str) -> DocumentBody:
        self.bodies_read.append(path)
        return DocumentBody(text=self.bodies.get(path, ""))


class FakeSettingsStore:
    """Holds settings in memory and counts the saves."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings if settings is not None else Settings()
        self.saved: list[Settings] = []

    def load(self) -> Settings:
        return self.settings

    def save(self, settings: Settings) -> None:
        self.settings = settings
        self.saved.append(settings)


class FakeLauncher:
    """Records what it was asked to open; answers as it was told to."""

    def __init__(self, accepts: bool = True) -> None:
        self.accepts = accepts
        self.launched: list[tuple[EditorChoice, str]] = []

    def launch(self, editor: EditorChoice, target: str) -> bool:
        self.launched.append((editor, target))
        return self.accepts


class FakeOpener:
    """Records the addresses it was handed."""

    def __init__(self, accepts: bool = True) -> None:
        self.accepts = accepts
        self.opened: list[str] = []

    def open(self, address: str) -> bool:
        self.opened.append(address)
        return self.accepts


class FakeProbe:
    """Says a fixed set of paths are there and nothing else is."""

    def __init__(self, present: tuple[str, ...] = ()) -> None:
        self.present = set(present)

    def exists(self, path: str) -> bool:
        return path in self.present


class FakePaths:
    """A home directory chosen by the test rather than by the machine."""

    def __init__(
        self,
        home: str = "/home/oliver",
        programs: tuple[str, ...] = (),
        system: str = "",
    ) -> None:
        self.home = home
        self.programs = programs
        self.system = system

    def home_directory(self) -> str:
        return self.home

    def program_directories(self) -> tuple[str, ...]:
        return self.programs

    def system_directory(self) -> str:
        return self.system
