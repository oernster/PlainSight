"""Write the version from VERSION into the GitHub Pages site.

A served page cannot read VERSION when it is rendered, so it carries a delimited
token this overwrites. It is idempotent: stamping a current file changes
nothing, so the build scripts can call it every time.

Scope is the site and nothing else. No document outside it carries a version at
all, which is why there is no root glob here.

It also versions each page's asset links. GitHub Pages lets a browser keep a
stylesheet for ten minutes, so a fresh page can arrive beside its stale CSS and
render broken. Every local `href="x.css"` or `src="x.js"` therefore carries
`?v=<hash>` of the file's content, taken with CRLF folded to LF so a Windows
checkout and the LF blob GitHub serves give the same hash.

    python stamp_version.py
"""

from __future__ import annotations

import hashlib
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

ASSET_HASH_LENGTH = 10
# A stylesheet or script reference; any query it already has is replaced.
ASSET_LINK = re.compile(
    r"""(?<![\w-])((?:href|src)=)(["'])"""
    r"""([^"'?#]+\.(?:css|js))(?:\?[^"'#]*)?(#[^"']*)?\2"""
)
# Only relative paths are local files: a scheme, `//` or a leading `/` is not.
NOT_RELATIVE = re.compile(r"^(?:[A-Za-z][A-Za-z0-9+.-]*:|/)")


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


def asset_hash(path: pathlib.Path) -> str:
    """The content hash of one asset, with CRLF folded to LF first."""
    if not path.is_file():
        raise FileNotFoundError(f"a site page links to a missing asset: {path}")
    data = path.read_bytes().replace(b"\r\n", b"\n")
    return hashlib.sha256(data).hexdigest()[:ASSET_HASH_LENGTH]


def version_assets(path: pathlib.Path) -> bool:
    """Hash every local asset link in one page; True when the page changed."""
    with path.open("r", encoding="utf-8", newline="") as handle:
        original = handle.read()

    def _link(match: re.Match[str]) -> str:
        attribute, quote, target, fragment = match.groups()
        if NOT_RELATIVE.match(target):
            return match.group(0)
        digest = asset_hash(path.parent / target)
        return f"{attribute}{quote}{target}?v={digest}{fragment or ''}{quote}"

    linked = ASSET_LINK.sub(_link, original)
    if linked == original:
        return False
    with path.open("w", encoding="utf-8", newline="") as handle:
        handle.write(linked)
    return True


def main() -> int:
    """Stamp every static file, naming the ones that changed."""
    version = read_version()
    changed = [path for path in stamped_files() if stamp(path, version)]
    for path in changed:
        print(f"stamped {path.relative_to(PROJECT_ROOT)} to {version}")
    if not changed:
        print(f"every stamped file already reads {version}")
    pages = [path for path in stamped_files() if path.suffix == ".html"]
    linked = [path for path in pages if version_assets(path)]
    for path in linked:
        print(f"versioned asset links in {path.relative_to(PROJECT_ROOT)}")
    if not linked:
        print("every asset link already carries its current hash")
    return 0


if __name__ == "__main__":
    sys.exit(main())
