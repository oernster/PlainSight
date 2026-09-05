"""Every kind this application reads has a reader that can read it.

A kind is added by adding a member to an enumeration, which is deliberately
cheap. The cost that would otherwise arrive later is a kind listed by discovery
with nothing able to open it, which shows as a document that appears in the
tree and fails the moment it is picked. This is that gap, closed at build time.
"""

from __future__ import annotations

from plainsight.__main__ import build_readers
from plainsight.domain.document import DocumentKind


def test_every_kind_has_a_reader() -> None:
    readers = build_readers()

    missing = [kind.name for kind in DocumentKind if kind not in readers]

    assert missing == []


def test_no_reader_is_kept_for_a_kind_that_does_not_exist() -> None:
    """The other direction: a kind removed leaves no reader behind it."""
    assert set(build_readers()) <= set(DocumentKind)


def test_each_kind_gets_a_reader_of_its_own() -> None:
    """A reader is told which kind it serves, so sharing one would mislead it.

    A single reader handed to two kinds would answer for both with whichever
    it was built for, which is exactly how a plain text file would come to be
    read as though it declared frontmatter.
    """
    readers = build_readers()

    assert len(set(map(id, readers.values()))) == len(readers)
