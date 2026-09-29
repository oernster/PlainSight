"""File names made from text somebody else wrote, safe on every platform.

A tag or a repository name arrives from GitHub, which is to say from whoever
typed it, so it is treated as foreign input: nothing in it may name another
directory, a device or a name Windows quietly rewrites. Windows is the
strictest platform this runs on, so a name safe there is safe everywhere.
"""

from __future__ import annotations

import re
import unicodedata

# Every character Windows refuses in a name, plus the control characters.
FORBIDDEN = re.compile(r'[<>:"/\\|?*\x00-\x1f\x7f]')
REPLACEMENT = "_"
# Windows drops these from the end of a name, so two names differing only there
# would be one file; they are removed before that can happen.
TRAILING = " ."
# Device names Windows reserves whatever suffix follows them. The superscript
# digits are included because Windows treats them as the plain ones.
RESERVED = frozenset(
    {"con", "prn", "aux", "nul"}
    | {f"{device}{digit}" for device in ("com", "lpt") for digit in "123456789¹²³"}
)
# Room for the date, the separator and a uniqueness suffix inside the 255 a
# file name may use, while keeping a whole path clear of Windows' classic 260.
MAX_STEM_LENGTH = 100
# A release's stem leaves this much of that room for ``_2``, ``_3`` and on, so a
# name made unique still reads back as one this module could have made.
UNIQUE_RESERVE = 8
FALLBACK = "release"

MARKDOWN_SUFFIX = ".md"
DATE_SEPARATOR = "_"
UNDATED = "undated"
DATE_LENGTH = len("YYYY-MM-DD")
UNIQUE_SEPARATOR = "_"
FIRST_DUPLICATE = 2


def safe_segment(
    text: str, fallback: str = FALLBACK, limit: int = MAX_STEM_LENGTH
) -> str:
    """``text`` as one path segment Windows accepts and reads back unchanged.

    A slash cannot survive, so no result names a directory; nothing is left
    that is only dots, so no result is ``..``; a reserved device name gets a
    leading underscore; the result is at most ``limit`` characters. Unicode is
    kept, normalised to its composed form so that two spellings of one name are
    one file.
    """
    cleaned = FORBIDDEN.sub(REPLACEMENT, unicodedata.normalize("NFC", text))
    cleaned = cleaned.strip()[:limit].rstrip(TRAILING)
    if not cleaned.strip(TRAILING):
        return fallback
    if cleaned.split(".", 1)[0].rstrip(" ").casefold() in RESERVED:
        cleaned = (REPLACEMENT + cleaned)[:limit].rstrip(TRAILING)
    return cleaned


def release_file_stem(published_at: str, tag: str) -> str:
    """``YYYY-MM-DD_<tag>``; ``undated_<tag>`` when the release carries no date.

    The date leads so the name says when as well as what, which is what a
    reader looking at the folder in a file dialogue wants. The order in the
    tree is not taken from it: that comes from the collection's own record.
    """
    day = published_at[:DATE_LENGTH] if published_at else UNDATED
    return safe_segment(
        f"{day}{DATE_SEPARATOR}{tag}", limit=MAX_STEM_LENGTH - UNIQUE_RESERVE
    )


def unique_name(stem: str, taken: set[str]) -> str:
    """``stem`` as a Markdown file name no name in ``taken`` already uses.

    Compared case folded, since Windows and macOS both treat two names that
    differ only in case as one file. The answer is added to ``taken``, so a
    caller allocating several in turn gets no two alike.
    """
    candidate = f"{stem}{MARKDOWN_SUFFIX}"
    counter = FIRST_DUPLICATE
    while candidate.casefold() in taken:
        candidate = f"{stem}{UNIQUE_SEPARATOR}{counter}{MARKDOWN_SUFFIX}"
        counter += 1
    taken.add(candidate.casefold())
    return candidate


def is_safe_file_name(name: str) -> bool:
    """Whether a name read back from disk is one this module could have made.

    A record of the files a collection holds can be edited by anyone, so a name
    in it is checked before any file is opened by it: it must be a Markdown
    file and survive ``safe_segment`` unchanged.
    """
    if not name.endswith(MARKDOWN_SUFFIX):
        return False
    stem = name[: -len(MARKDOWN_SUFFIX)]
    return bool(stem) and safe_segment(stem, fallback="") == stem
