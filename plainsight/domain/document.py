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


class Presentation(Enum):
    """How a kind's text becomes what a reading surface shows.

    Three answers rather than a flag, because there are three of them: text
    laid out for the page, text that is its own layout and text that is
    already the thing the surface renders. A flag carried two of these and had
    nowhere to put the third.
    """

    LAID_OUT = "laid out"
    AS_TYPED = "as typed"
    ALREADY_HTML = "already html"


class DocumentKind(Enum):
    """A kind of file this application knows how to read.

    Every suffix that names a kind is the member's own value, so adding a kind
    is adding a member and nothing else. Discovery, rendering and the reading
    pane each ask this enumeration rather than holding a list of suffixes of
    their own, which is what stops the three drifting apart as more kinds
    arrive.

    A kind may answer to more than one suffix. ``.htm`` and ``.html`` name the
    same thing, so a reader who opens one and not the other would be reading a
    distinction that exists nowhere outside this file.
    """

    MARKDOWN = (".md",)
    PLAIN_TEXT = (".txt",)
    HTML = (".html", ".htm")

    @property
    def suffixes(self) -> tuple[str, ...]:
        """Every lower cased file suffix that names this kind."""
        return self.value

    @property
    def presentation(self) -> Presentation:
        """How this kind's text reaches the reading surface.

        HTML is already what the surface renders, so it is handed over as it
        stands rather than being rewritten into itself.
        """
        if self is DocumentKind.MARKDOWN:
            return Presentation.LAID_OUT
        if self is DocumentKind.HTML:
            return Presentation.ALREADY_HTML
        return Presentation.AS_TYPED

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
        author's own layout, so it is shown exactly as it came; HTML carries
        its own layout too, in its markup rather than in its line breaks.
        """
        return self.presentation is Presentation.LAID_OUT


def readable_suffixes() -> tuple[str, ...]:
    """Every suffix this application reads, in the order the kinds declare.

    Here rather than in the file dialogue that shows them, so the set a chooser
    offers cannot drift from the set discovery accepts.
    """
    return tuple(suffix for kind in DocumentKind for suffix in kind.suffixes)


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
        if f"{separator}{suffix}" in kind.suffixes:
            return kind
    return None


class InvalidDocument(ValueError):
    """A document was described in a way that cannot be true."""


@dataclass(frozen=True, slots=True)
class DocumentSummary:
    """What a listing knows about a document without reading all of it.

    A listing needs what a document calls itself and whether it can be opened
    at all. It does not need the text. That is the whole distinction this type
    exists to hold: a kind whose text must be extracted rather than decoded
    would otherwise pay that extraction for every document in a tree in order
    to show one of them.
    """

    declared_name: str = ""
    description: str = ""
    declared_fields: tuple[tuple[str, str], ...] = field(default=())
    failure: str = ""


@dataclass(frozen=True, slots=True)
class DocumentBody:
    """A document's text, else the reason there is none to give.

    The reason travels with the absence rather than being worked out from it.
    An empty string on its own cannot tell a file that went away from one that
    is locked or one that holds no text a machine can reach; those want
    different words in front of a reader.
    """

    text: str = ""
    failure: str = ""


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

    ``fingerprint`` says what the file was when it was listed, so that a
    document compares equal to itself and unequal to the same file edited
    since. The reading pane leans on exactly that: it leaves a document that
    has not changed alone, half read and at the place the reader had reached;
    it draws one that has changed again. The body used to carry that weight
    by being part of the value; it is fetched when a document is opened now,
    so something else has to; a fingerprint costs one look at the file
    rather than all of it.

    What goes in it is infrastructure's business. The domain reads nothing
    from disk, so it holds the answer without knowing how it was arrived at.
    """

    name: str
    path: str
    kind: DocumentKind
    fingerprint: str = ""
    declared_name: str = ""
    description: str = ""
    failure: str = ""
    declared_fields: tuple[tuple[str, str], ...] = field(default=())

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise InvalidDocument("a document needs a name")
        if not self.path.strip():
            raise InvalidDocument("a document needs a path")

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
