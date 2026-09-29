"""One published release, as it arrived, then as the document it becomes.

The release notes are the point, so the header written above them is small and
the notes themselves go through untouched: GitHub's Markdown is already what
the reading pane renders, so converting it into anything else and back would
only lose whatever the round trip did not understand.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from html import escape

# A moment as GitHub states one, normalised at the boundary to UTC with no
# fraction, so that comparing two as text is comparing them in time.
MOMENT_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z")
MONTH_NAMES = (
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
)
YEAR = slice(0, 4)
MONTH = slice(5, 7)
DAY = slice(8, 10)

NO_NOTES = "No release notes were provided for this release."
SOURCE_NAME = "GitHub"
# A line ending in two spaces is Markdown's own line break, which keeps the
# header lines on lines of their own without a paragraph's gap between each.
LINE_BREAK = "  \n"
RULE = "---"
# Only a link that goes where it says is written as one. Anything else is named
# as its source in plain words.
RELEASE_PAGE = re.compile(r"https://github\.com/[^\s<>()\[\]]+")
# The characters that would make a title or a tag mean something to Markdown
# where they sit, inside a line that already has its own start: emphasis, code,
# a link and the closing hashes a heading may carry. Each is written escaped so
# plain text arrives as the plain text it was; the rest are left alone so the
# file still reads cleanly in an editor.
MARKDOWN_SPECIALS = re.compile(r"([\\`*_\[\]#])")
WHITESPACE = re.compile(r"\s+")


class InvalidRelease(ValueError):
    """A release that cannot be named or placed in time as stated."""


@dataclass(frozen=True, slots=True)
class Release:
    """A published release: what it is called, when and the notes it carries.

    ``published_at`` is empty for a release GitHub gives no date for, else an
    exact UTC moment in ``MOMENT_PATTERN``'s form. ``source_id`` is GitHub's own
    number for the release, which stays the same when the tag or the title is
    edited; that is what makes it the identity a refresh goes by.
    """

    source_id: int
    tag: str
    title: str = ""
    published_at: str = ""
    prerelease: bool = False
    body: str = ""
    source_url: str = ""

    def __post_init__(self) -> None:
        if not self.tag.strip():
            raise InvalidRelease("A release has to carry a tag.")
        if self.published_at and not MOMENT_PATTERN.fullmatch(self.published_at):
            raise InvalidRelease(f"Not a moment: {self.published_at!r}")

    @property
    def heading(self) -> str:
        """The title where it has one; its tag where it has none."""
        title = WHITESPACE.sub(" ", self.title).strip()
        return title or self.tag


def display_date(published_at: str) -> str:
    """``29 September 2026`` from a moment; empty from no moment at all."""
    if not published_at:
        return ""
    month = MONTH_NAMES[int(published_at[MONTH]) - 1]
    return f"{int(published_at[DAY])} {month} {published_at[YEAR]}"


def plain(text: str) -> str:
    """Text written so Markdown shows it as it is rather than reading it.

    One line, since a line break in a title would end the heading and start
    whatever the rest of it happened to spell.
    """
    single = escape(WHITESPACE.sub(" ", text).strip(), quote=False)
    return MARKDOWN_SPECIALS.sub(r"\\\1", single)


def release_markdown(release: Release) -> str:
    """The whole document: a small header, a rule, then the notes unchanged."""
    lines = [f"**Tag:** {plain(release.tag)}"]
    if release.published_at:
        lines.append(f"**Released:** {display_date(release.published_at)}")
    if release.prerelease:
        lines.append("**Pre-release:** Yes")
    lines.append(f"**Source:** {_source(release.source_url)}")
    notes = release.body if release.body.strip() else NO_NOTES
    ending = "" if notes.endswith("\n") else "\n"
    return (
        f"# {plain(release.heading)}\n\n"
        f"{LINE_BREAK.join(lines)}\n\n"
        f"{RULE}\n\n"
        f"{notes}{ending}"
    )


def _source(address: str) -> str:
    """A link to the release's own page where there is a safe one to give."""
    if RELEASE_PAGE.fullmatch(address):
        return f"[{SOURCE_NAME}]({address})"
    return SOURCE_NAME
