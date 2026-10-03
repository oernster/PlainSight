"""What a document may reach: the links it hands on and the files it may show.

A document is somebody else's text, so everything it names is somebody else's
choice. Two rules follow, both stated here and nowhere else.

A link is handed on only when it is a web page or a mail. Every other scheme is
a handler on this computer that a stranger would be choosing to start, so it
does nothing; a link within the page moves the reader to that place in it.

A file the document embeds, a picture or a background, is read from this
computer only. Named absolutely, it is read where it says, provided that is a
local path. Named relatively, it is looked for from the document's own folder
and nowhere else, never from wherever the application happened to start. It
may climb out of that folder with ``..`` while where it lands is still a local
path; it is refused once it lands on a network path outside the document's own
folder. A document opened from a share therefore shows the pictures in its own
folder (where the reader chose to read) and nothing further across the
network. Anything naming a host (``file://host``, ``//host`` or ``\\\\host``)
is refused before it is read; so is any scheme other than ``file``.

One limit is stated rather than hidden: a drive letter the desktop has mapped to
a share looks exactly like a local drive from its name, so it is read as one.
Telling them apart needs the operating system, which the domain does not ask.
"""

from __future__ import annotations

import re
from enum import Enum
from urllib.parse import unquote, urlsplit

FOLLOWED_SCHEMES = frozenset({"https", "http", "mailto"})
NEEDS_A_HOST = frozenset({"https", "http"})
FILE_SCHEME = "file"
INLINE_SCHEME = "data"
LOCAL_HOSTS = frozenset({"", "localhost"})
IN_PAGE_MARK = "#"
SEPARATOR = "/"
BACKSLASH = "\\"
NETWORK_PREFIX = SEPARATOR * 2
CURRENT = "."
PARENT = ".."

# A scheme is a letter then letters, digits, plus, minus or dots, then a
# colon. A single letter is a Windows drive rather than a scheme.
_SCHEME = re.compile(r"^([A-Za-z][A-Za-z0-9+.\-]*):")
_DRIVE = re.compile(r"^[A-Za-z]:")
_DRIVE_ROOT = re.compile(r"^[A-Za-z]:/")
# A file address carries a drive after its leading slash: /C:/...
_FILE_URL_DRIVE = re.compile(r"^/[A-Za-z]:/")
DRIVE_LETTER_LENGTH = 1
# A share's root is its host and the share's own name: //host/share/.
SHARE_ROOT_PARTS = 2


class LinkAction(Enum):
    """What a click on a link in a document does."""

    FOLLOW = "follow"
    IN_PAGE = "in page"
    IGNORE = "ignore"


def link_action(address: str) -> LinkAction:
    """Hand on a web page or a mail, stay within the page, else do nothing."""
    text = address.strip()
    if text.startswith(IN_PAGE_MARK):
        return LinkAction.IN_PAGE
    scheme = _scheme_of(text)
    if scheme not in FOLLOWED_SCHEMES:
        return LinkAction.IGNORE
    if scheme in NEEDS_A_HOST and not urlsplit(text).netloc:
        return LinkAction.IGNORE
    return LinkAction.FOLLOW


def is_inline(source: str) -> bool:
    """Whether a source carries its own bytes and names no file at all."""
    return _scheme_of(source.strip()) == INLINE_SCHEME


def resource_path(source: str, document_path: str | None) -> str | None:
    """The local path an embedded file may be read from; None when refused.

    ``document_path`` is the document doing the embedding; a relative source is
    looked for from its folder. With no document a relative source is refused,
    since there is no folder it could honestly mean.
    """
    path = _path_named_by(source.strip())
    if path is None:
        return None
    path = _forward(path)
    if path.startswith(NETWORK_PREFIX):
        return None
    if _is_absolute(path):
        return _normalised(path)
    if _DRIVE.match(path) or document_path is None:
        return None
    document = _forward(document_path)
    if not _is_absolute(document):
        return None
    return _beside(path, _normalised(_folder_of(document)))


def _forward(path: str) -> str:
    """Every backslash read as the separator, since Windows takes either."""
    return SEPARATOR.join(path.split(BACKSLASH))


def _is_absolute(path: str) -> bool:
    """Whether a path starts at a root: a slash or a drive and a slash."""
    return path.startswith(SEPARATOR) or _DRIVE_ROOT.match(path) is not None


def _scheme_of(text: str) -> str | None:
    """The scheme an address names, lower case; None for a drive or for none."""
    match = _SCHEME.match(text)
    if match is None or len(match.group(1)) == DRIVE_LETTER_LENGTH:
        return None
    return match.group(1).lower()


def _path_named_by(source: str) -> str | None:
    """The path a source names, decoded once; None for a host or a scheme."""
    if not source:
        return None
    scheme = _scheme_of(source)
    if scheme is None:
        return unquote(source)
    if scheme != FILE_SCHEME:
        return None
    parts = urlsplit(source)
    if parts.netloc.lower() not in LOCAL_HOSTS:
        return None
    path = unquote(parts.path)
    return path[len(SEPARATOR) :] if _FILE_URL_DRIVE.match(path) else path


def _beside(relative: str, folder: str) -> str | None:
    """A relative path read from ``folder``, under the rule the module states."""
    # Stripped first, so a folder that is a root ("/", "C:/") never doubles
    # its separator into the start of a network path.
    base = folder.rstrip(SEPARATOR) + SEPARATOR
    joined = _normalised(base + relative)
    inside = joined.startswith(base)
    if inside or not joined.startswith(NETWORK_PREFIX):
        return joined
    return None


def _folder_of(document_path: str) -> str:
    """The folder a document sits in, keeping the separator that ends it.

    Kept so a document at the root of a drive has ``C:/`` for its folder, which
    is a root, rather than ``C:``, which is not.
    """
    folder, separator, _name = document_path.rpartition(SEPARATOR)
    return folder + separator


def _normalised(path: str) -> str:
    """``.`` and ``..`` worked out, never climbing above the path's own root.

    The root is a drive, a single slash or a share (two slashes, a host and
    the share name). A share is a root because climbing above it would name
    another host, which is not a place inside this one.
    """
    root, rest = _split_root(path)
    kept: list[str] = []
    for part in rest.split(SEPARATOR):
        if part in ("", CURRENT):
            continue
        if part == PARENT:
            if kept:
                kept.pop()
            continue
        kept.append(part)
    return root + SEPARATOR.join(kept)


def _split_root(path: str) -> tuple[str, str]:
    """A path's root (ending in a separator) and everything after it."""
    if path.startswith(NETWORK_PREFIX):
        parts = path[len(NETWORK_PREFIX) :].split(SEPARATOR, SHARE_ROOT_PARTS)
        root = NETWORK_PREFIX + SEPARATOR.join(parts[:SHARE_ROOT_PARTS]) + SEPARATOR
        return root, SEPARATOR.join(parts[SHARE_ROOT_PARTS:])
    if _DRIVE_ROOT.match(path):
        drive_end = path.index(SEPARATOR) + len(SEPARATOR)
        return path[:drive_end], path[drive_end:]
    return SEPARATOR, path[len(SEPARATOR) :]
