"""One document: the text of a file, whatever it declares and how to read it.

Paths are held as plain strings. The domain reads nothing from disk, so it has
no use for a path object's behaviour and no business importing one.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

HEADER_FIELD_CHARS_PER_LINE = 100
HEADER_FIELD_MAX_LINES = 3
HEADER_FIELD_LIMIT = HEADER_FIELD_CHARS_PER_LINE * HEADER_FIELD_MAX_LINES
SHOWN_ALREADY = frozenset({"name", "description"})
SUFFIX_SEPARATOR = "."


class DocumentKind(Enum):
    """A kind of file this application knows how to read.

    The suffix is the member's own value, so adding a kind is adding a member
    and nothing else. Discovery, rendering and the reading pane each ask this
    enumeration rather than holding a list of suffixes of their own, which is
    what stops the three drifting apart as more kinds arrive.
    """

    MARKDOWN = ".md"
    PLAIN_TEXT = ".txt"

    @property
    def suffix(self) -> str:
        """The lower cased file suffix that names this kind."""
        return self.value

    @property
    def declares_fields(self) -> bool:
        """Whether a document of this kind can carry a frontmatter block.

        Only Markdown does. A leading fence in a plain text file is three
        hyphens somebody typed, so reading it as a block of fields would
        silently swallow the opening of the document.
        """
        return self is DocumentKind.MARKDOWN

    @property
    def reflows(self) -> bool:
        """Whether the text is laid out for the page rather than kept as typed.

        Markdown is laid out, so an over-long passage in it may be given
        somewhere to breathe. Plain text carries its own line breaks and is the
        author's own layout, so it is shown exactly as it came.
        """
        return self is DocumentKind.MARKDOWN


def kind_of(file_name: str) -> DocumentKind | None:
    """The kind this file name names; None when it is not one that is read.

    Matched on the suffix alone and case insensitively, so ``NOTES.MD`` reads
    as Markdown. A name that is nothing but a suffix has no stem and is not a
    document, which is what keeps a bare ``.md`` out of the list.
    """
    stem, separator, suffix = file_name.lower().rpartition(SUFFIX_SEPARATOR)
    if not separator or not stem:
        return None
    for kind in DocumentKind:
        if f"{separator}{suffix}" == kind.suffix:
            return kind
    return None


class InvalidDocument(ValueError):
    """A document was described in a way that cannot be true."""


@dataclass(frozen=True, slots=True)
class Document:
    """A document as the reader knows it.

    ``name`` is the file's own name, which is what the tree shows: the tree
    mirrors the folders on disk, so a row that did not carry the file name
    would be a row the reader could not find again in a file dialogue.

    ``declared_name`` is what a frontmatter block called it, where there is
    one. It heads the reading pane, so a skill opens under the name it declares
    while still listing as the file it is.

    ``failure`` carries the reason a document could not be read or parsed. A
    document with a failure is still a document and is still listed, because
    the reader neither caused it nor can fix it from here; the reason is what
    gets shown in place of the body.
    """

    name: str
    path: str
    kind: DocumentKind
    body: str
    declared_name: str = ""
    description: str = ""
    failure: str = ""
    declared_fields: tuple[tuple[str, str], ...] = field(default=())

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise InvalidDocument("a document needs a name")
        if not self.path.strip():
            raise InvalidDocument("a document needs a path")
        if not self.body.strip() and not self.failure.strip():
            raise InvalidDocument(
                "a document needs either a body or a failure to report"
            )

    @property
    def title(self) -> str:
        """What the reading pane heads it with: the declared name, else the file."""
        return self.declared_name.strip() or self.name

    @property
    def is_readable(self) -> bool:
        """Whether the file was read and parsed without trouble."""
        return not self.failure

    @property
    def sort_key(self) -> str:
        """The key a folder orders its documents by: the file name, case folded."""
        return self.name.casefold()

    @property
    def header_fields(self) -> tuple[tuple[str, str], ...]:
        """Declared fields short enough to read as a header row."""
        return tuple(
            pair for pair in self._extra_fields if len(pair[1]) <= HEADER_FIELD_LIMIT
        )

    @property
    def long_fields(self) -> tuple[tuple[str, str], ...]:
        """Declared fields too long for a header row.

        A frontmatter value has no length limit and the longest in the library
        this was measured against runs to eleven thousand characters on one
        line. Shown among the header rows it buries the document the reader
        opened, so it is separated out here and given a section of its own.
        """
        return tuple(
            pair for pair in self._extra_fields if len(pair[1]) > HEADER_FIELD_LIMIT
        )

    @property
    def _extra_fields(self) -> tuple[tuple[str, str], ...]:
        """Declared fields beyond the two the header already shows outright."""
        return tuple(
            (key, value)
            for key, value in self.declared_fields
            if key not in SHOWN_ALREADY
        )
