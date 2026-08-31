"""Write the version from VERSION into the GitHub Pages site.

A served page cannot read VERSION when it is rendered, so it carries a delimited
token this overwrites. It is idempotent: stamping a current file changes
nothing, so the build scripts can call it every time.

Scope is the site and nothing else. No document outside it carries a version at
all, which is why there is no root glob here.

    python stamp_version.py
"""

from __future__ import annotations

import pathlib
import re
import sys

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent
VERSION_FILE = PROJECT_ROOT / "VERSION"
FALLBACK_VERSION = "0.0.0-dev"

OPEN_TOKEN = "<!--VERSION-->"
CLOSE_TOKEN = "<!--/VERSION-->"
TOKEN = re.compile(re.escape(OPEN_TOKEN) + r".*?" + re.escape(CLOSE_TOKEN), re.DOTALL)

# The GitHub Pages tree only. No document outside the site may carry version
# data at all, so there is nothing at the repository root to stamp; a root glob
# here would invite exactly the version strings that rule forbids.
STAMPED_GLOBS = ("docs/**/*.html", "docs/**/*.md")
EXCLUDED_NAMES = frozenset({"NOTES.md"})


def read_version() -> str:
    """The one real version string; else the development sentinel."""
    if not VERSION_FILE.is_file():
        return FALLBACK_VERSION
    return VERSION_FILE.read_text(encoding="utf-8").strip() or FALLBACK_VERSION


def stamped_files() -> list[pathlib.Path]:
    """Every file that may carry a version token."""
    found: list[pathlib.Path] = []
    for pattern in STAMPED_GLOBS:
        found.extend(
            path
            for path in PROJECT_ROOT.glob(pattern)
            if path.is_file() and path.name not in EXCLUDED_NAMES
        )
    return sorted(set(found))


def stamp(path: pathlib.Path, version: str) -> bool:
    """Overwrite every token in one file; True when the file changed."""
    original = path.read_text(encoding="utf-8")
    stamped = TOKEN.sub(f"{OPEN_TOKEN}{version}{CLOSE_TOKEN}", original)
    if stamped == original:
        return False
    path.write_text(stamped, encoding="utf-8")
    return True


def main() -> int:
    """Stamp every static file, naming the ones that changed."""
    version = read_version()
    changed = [path for path in stamped_files() if stamp(path, version)]
    for path in changed:
        print(f"stamped {path.relative_to(PROJECT_ROOT)} to {version}")
    if not changed:
        print(f"every stamped file already reads {version}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
