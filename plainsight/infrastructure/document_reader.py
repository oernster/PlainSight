"""Reading one file of one kind: what it declares, then its text on demand.

A reader per kind, rather than one reader asked to recognise what it was given.
The kinds read today are all text and share this one implementation, which is
told which kind it serves; a kind that must be extracted rather than decoded
brings its own reader and this one never learns of it.

The two halves are apart because they cost differently. Summarising happens for
every document beneath a chosen folder, so it must stay cheap; reading a body
happens for the one document a reader opened, so it may be as dear as that kind
demands.
"""

from __future__ import annotations

from pathlib import Path

from ..domain.document import DocumentBody, DocumentKind, DocumentSummary
from ..domain.parsing import EMPTY_FIELDS, ParsedDocument, parse_document

UNREADABLE_TEXT = "This file could not be read as text."
MISSING_TEXT = "This file could not be opened."
EMPTY_TEXT = "This file holds no text."
EMPTY_MARKDOWN_TEXT = "This file holds no text beneath its frontmatter."


class TextDocumentReader:
    """A file that is text: decoded, then split into what it declares.

    Told which kind it serves, because that is what settles whether a leading
    fence is a block of fields or the opening of the document; it also settles
    which of the two ways of being empty applies.
    """

    def __init__(self, kind: DocumentKind) -> None:
        self._kind = kind

    def summarise(self, path: str) -> DocumentSummary:
        """What this file declares, plus any reason it cannot be shown.

        Decoding the file is what says whether it can be read at all, so this
        costs a read for a text kind. That is the honest price here and it was
        measured at 10ms over a tree of 59 documents; what it no longer costs
        is keeping every one of those bodies afterwards.
        """
        text, failure = self._text(path)
        parsed = self._parse(text)
        if not failure and not parsed.body.strip():
            failure = EMPTY_MARKDOWN_TEXT if self._kind.declares_fields else EMPTY_TEXT
        return DocumentSummary(
            declared_name=parsed.name,
            description=parsed.description,
            declared_fields=tuple(parsed.frontmatter.items()),
            failure=failure,
        )

    def read_body(self, path: str) -> DocumentBody:
        """The text beneath whatever this kind declares, else why there is none."""
        text, failure = self._text(path)
        if failure:
            return DocumentBody(failure=failure)
        return DocumentBody(text=self._parse(text).body)

    def _parse(self, text: str) -> ParsedDocument:
        """The text split into fields and body, where this kind declares fields."""
        if self._kind.declares_fields:
            return parse_document(text)
        return ParsedDocument(frontmatter=EMPTY_FIELDS, body=text)

    def _text(self, path: str) -> tuple[str, str]:
        """The file's text with no failure; else empty text with a reason."""
        try:
            return Path(path).read_text(encoding="utf-8"), ""
        except UnicodeDecodeError:
            return "", UNREADABLE_TEXT
        except OSError:
            return "", MISSING_TEXT
