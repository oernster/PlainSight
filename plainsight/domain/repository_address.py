"""Which GitHub repository an address names, read from what a reader pasted.

A reader copies an address out of a browser, so the forms accepted are the ones
a browser and a README actually carry: the full address with or without its
scheme, with or without a trailing slash, the ``owner/repository`` shorthand
and a repository's own sub-pages such as its releases. Anything else is refused
with the reason, rather than guessed at: an address read as the wrong
repository imports the wrong history without a word said.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

HOSTS = frozenset({"github.com", "www.github.com"})
SCHEMES = frozenset({"https", "http"})
SCHEME_SEPARATOR = "://"
CLONE_SUFFIX = ".git"
WEB_ROOT = "https://github.com"
# An owner, then the repository: the two segments a repository address holds.
REPOSITORY_SEGMENTS = 2

# GitHub's own rules: an account name is letters, digits and hyphens, starting
# with a letter or digit, at most 39 characters; a repository name is letters,
# digits, dots, hyphens and underscores, at most 100.
OWNER_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9-]{0,38}")
REPOSITORY_PATTERN = re.compile(r"[A-Za-z0-9._-]{1,100}")
DOT_NAMES = frozenset({".", ".."})

# The pages beneath a repository that still name that repository. Anything
# after them is the page's own business and is set aside with them.
REPOSITORY_PAGES = frozenset(
    {
        "releases",
        "tags",
        "tree",
        "blob",
        "commits",
        "commit",
        "issues",
        "pulls",
        "pull",
        "wiki",
        "actions",
        "discussions",
        "branches",
        "security",
        "pulse",
        "graphs",
        "projects",
        "labels",
        "milestones",
        "compare",
        "network",
        "activity",
        "stargazers",
        "forks",
        "watchers",
    }
)

# First segments that are GitHub's own pages rather than an account, so that
# ``github.com/orgs/acme`` is never read as a repository called acme.
SITE_PAGES = frozenset(
    {
        "orgs",
        "users",
        "settings",
        "marketplace",
        "topics",
        "sponsors",
        "features",
        "login",
        "logout",
        "signup",
        "explore",
        "notifications",
        "new",
        "search",
        "collections",
        "trending",
        "apps",
        "enterprise",
        "pricing",
        "about",
    }
)

EMPTY = "Paste the address of a GitHub repository."
NO_OWNER = "The address names no owner. Paste the repository's own address."
NO_REPOSITORY = "The address names an owner but no repository."
OTHER_HOST = "Only repositories on github.com can be imported."
OTHER_SCHEME = "The address must start with https://github.com/."
NOT_A_REPOSITORY = "That address is not a GitHub repository's page."
BAD_OWNER = "That owner name is not one GitHub allows."
BAD_REPOSITORY = "That repository name is not one GitHub allows."


class InvalidRepositoryAddress(ValueError):
    """An address that names no single GitHub repository; says why."""


@dataclass(frozen=True, slots=True)
class RepositoryAddress:
    """One GitHub repository, named by its owner and its own name."""

    owner: str
    name: str

    def __post_init__(self) -> None:
        if not OWNER_PATTERN.fullmatch(self.owner):
            raise InvalidRepositoryAddress(BAD_OWNER)
        if self.name in DOT_NAMES or not REPOSITORY_PATTERN.fullmatch(self.name):
            raise InvalidRepositoryAddress(BAD_REPOSITORY)

    @property
    def web_url(self) -> str:
        """The repository's own page."""
        return f"{WEB_ROOT}/{self.owner}/{self.name}"

    def same_repository(self, other: RepositoryAddress) -> bool:
        """Whether both name one repository; GitHub ignores case in both parts."""
        return (self.owner.casefold(), self.name.casefold()) == (
            other.owner.casefold(),
            other.name.casefold(),
        )


def parse_repository_address(text: str) -> RepositoryAddress:
    """The repository this address names; raises with the reason when none."""
    stripped = text.strip()
    if not stripped:
        raise InvalidRepositoryAddress(EMPTY)
    if SCHEME_SEPARATOR in stripped:
        segments = _web_segments(stripped)
    elif stripped.casefold().split("/", 1)[0] in HOSTS:
        segments = _path_segments(stripped.split("/", 1)[1] if "/" in stripped else "")
    else:
        segments = _shorthand_segments(stripped)
    return _repository(segments)


def _web_segments(text: str) -> list[str]:
    """The path of a full address, after its scheme and host are checked."""
    scheme, rest = text.split(SCHEME_SEPARATOR, 1)
    if scheme.casefold() not in SCHEMES:
        raise InvalidRepositoryAddress(OTHER_SCHEME)
    host, _, path = rest.partition("/")
    if host.casefold() not in HOSTS:
        raise InvalidRepositoryAddress(OTHER_HOST)
    return _path_segments(path)


def _path_segments(path: str) -> list[str]:
    """The segments of a path; a query, a fragment and one trailing slash go.

    A browser adds a query or a fragment to a repository's page as the reader
    moves around it, so neither changes which repository is meant. An empty
    segment anywhere else is a malformed address rather than a typing slip to
    tidy away.
    """
    for marker in ("#", "?"):
        path = path.split(marker, 1)[0]
    path = path.removesuffix("/")
    if not path:
        return []
    segments = path.split("/")
    if any(not segment for segment in segments):
        raise InvalidRepositoryAddress(NOT_A_REPOSITORY)
    return segments


def _shorthand_segments(text: str) -> list[str]:
    """``owner/repository`` and nothing more, since nothing else is certain."""
    segments = _path_segments(text)
    if len(segments) == 1:
        raise InvalidRepositoryAddress(NO_OWNER)
    if len(segments) > REPOSITORY_SEGMENTS:
        raise InvalidRepositoryAddress(NOT_A_REPOSITORY)
    return segments


def _repository(segments: list[str]) -> RepositoryAddress:
    """The repository named by a path's segments; raises saying why if none."""
    if not segments:
        raise InvalidRepositoryAddress(NO_OWNER)
    owner = segments[0]
    if owner.casefold() in SITE_PAGES:
        raise InvalidRepositoryAddress(NOT_A_REPOSITORY)
    if len(segments) == 1:
        raise InvalidRepositoryAddress(NO_REPOSITORY)
    name = segments[1]
    page = segments[REPOSITORY_SEGMENTS] if len(segments) > REPOSITORY_SEGMENTS else ""
    if page and page.casefold() not in REPOSITORY_PAGES:
        raise InvalidRepositoryAddress(NOT_A_REPOSITORY)
    if name.casefold().endswith(CLONE_SUFFIX) and len(name) > len(CLONE_SUFFIX):
        name = name[: -len(CLONE_SUFFIX)]
    return RepositoryAddress(owner=owner, name=name)
