"""Writing a file whole or not at all.

The bytes go to a temporary file beside the target, then a replace moves it
into place in one step. A process that dies halfway leaves the previous file
intact rather than a half-written one the next reader cannot use.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

# Hidden, so a temporary file left by a crash is never listed as a document.
TEMPORARY_PREFIX = "."
TEMPORARY_SUFFIX = ".tmp"


def write_atomically(path: Path, data: bytes) -> None:
    """Replace ``path`` with ``data``; raises ``OSError`` leaving it as it was."""
    handle, temporary = tempfile.mkstemp(
        dir=str(path.parent), prefix=TEMPORARY_PREFIX, suffix=TEMPORARY_SUFFIX
    )
    try:
        with os.fdopen(handle, "wb") as stream:
            stream.write(data)
        os.replace(temporary, path)
    except OSError:
        os.unlink(temporary)
        raise
