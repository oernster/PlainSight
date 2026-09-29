"""Every published release of a repository, asked of GitHub's REST API.

The documented releases endpoint rather than the rendered pages: an API answer
is a contract, where scraping reads whatever GitHub's page happens to look like
this month. No token is asked for or sent; public releases need none.

Everything that comes back is foreign input. A page is refused unread past a
size cap, since that size is decided before a byte of it can be checked; every
field of every release is checked before it is used; a next page is followed
only while it stays on the API's own host. A failure of any kind is raised as
the problem it is, so the reader is told what actually happened.
"""

from __future__ import annotations

import http.client
import json
import re
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from datetime import UTC, datetime
from http import HTTPStatus
from typing import Any
from urllib.parse import quote

from ..application.release_import import (
    GitHubUnavailable,
    ImportCancelled,
    ImportProblem,
    MalformedResponse,
    NetworkUnavailable,
    RateLimited,
    RepositoryInaccessible,
    RepositoryNotFound,
    TimedOut,
)
from ..domain.release import InvalidRelease, Release
from ..domain.repository_address import RepositoryAddress

API_ROOT = "https://api.github.com"
# GitHub's own maximum per page. It keeps the number of requests as small as it
# can be, so an import spends as little of the hourly allowance as it can.
PAGE_SIZE = 100
# Ten thousand releases. A repository with more is not one this is for; a
# pagination loop that never ends is stopped here rather than followed.
MAX_PAGES = 100
TIMEOUT_SECONDS = 15
# A release body is capped by GitHub at 125,000 characters, so a full page of
# the largest is well inside this; anything beyond it is not a page of releases.
MAX_PAGE_BYTES = 32 * 1024 * 1024
HEADERS = {
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
    "User-Agent": "PlainSight",
}

LINK_HEADER = "Link"
REMAINING_HEADER = "X-RateLimit-Remaining"
RESET_HEADER = "X-RateLimit-Reset"
RETRY_AFTER_HEADER = "Retry-After"
SPENT = "0"
NEXT_LINK = re.compile(r'<([^>]+)>\s*;\s*rel="next"')
MOMENT_FORMAT = "%Y-%m-%dT%H:%M:%SZ"

ID_FIELD = "id"
TAG_FIELD = "tag_name"
NAME_FIELD = "name"
PUBLISHED_FIELD = "published_at"
DRAFT_FIELD = "draft"
PRERELEASE_FIELD = "prerelease"
BODY_FIELD = "body"
PAGE_FIELD = "html_url"

Opener = Callable[..., Any]
Clock = Callable[[], float]


class GitHubReleaseHistory:
    """Every published release of a repository, every page followed."""

    def __init__(
        self, opener: Opener | None = None, clock: Clock | None = None
    ) -> None:
        # Both are injected so no test reaches the network or the wall clock;
        # the defaults are the standard library, so nothing is added to ship it.
        self._opener = urllib.request.urlopen if opener is None else opener
        self._clock = time.time if clock is None else clock

    def releases(
        self,
        address: RepositoryAddress,
        on_page: Callable[[int], None],
        cancelled: Callable[[], bool],
    ) -> tuple[Release, ...]:
        """All of them, drafts left out; raises an ``ImportProblem`` otherwise."""
        url = first_page(address)
        found: list[Release] = []
        for _page in range(MAX_PAGES):
            if cancelled():
                raise ImportCancelled()
            payload, link = self._fetch(url)
            found.extend(releases_in(payload))
            on_page(len(found))
            following = next_page(link)
            if following is None:
                return tuple(found)
            url = following
        raise MalformedResponse(f"More than {MAX_PAGES} pages of releases")

    def _fetch(self, url: str) -> tuple[object, str]:
        """One page decoded, with the header naming the next; raises otherwise."""
        request = urllib.request.Request(url, headers=HEADERS)
        try:
            with self._opener(request, timeout=TIMEOUT_SECONDS) as response:
                raw = response.read(MAX_PAGE_BYTES + 1)
                link = response.headers.get(LINK_HEADER) or ""
        except urllib.error.HTTPError as error:
            raise self._refusal(error.code, error.headers) from error
        except urllib.error.URLError as error:
            if isinstance(error.reason, TimeoutError):
                raise TimedOut() from error
            raise NetworkUnavailable() from error
        except TimeoutError as error:
            raise TimedOut() from error
        except (OSError, http.client.HTTPException) as error:
            raise NetworkUnavailable() from error
        if len(raw) > MAX_PAGE_BYTES:
            raise MalformedResponse("A page larger than any page of releases")
        try:
            return json.loads(raw.decode("utf-8")), link
        except ValueError as error:
            raise MalformedResponse("A page that is not JSON") from error

    def _refusal(self, status: int, headers: Any) -> ImportProblem:
        """The problem a refusal from GitHub stands for.

        GitHub answers a spent allowance with 403 and a zero remaining count;
        else with 429. Both carry when the allowance returns, which is the one
        thing the reader needs to know. A private repository is reported as
        not found, by GitHub's own choice, so the two cannot be told apart.
        """
        remaining = _header(headers, REMAINING_HEADER)
        retry_after = _header(headers, RETRY_AFTER_HEADER)
        limited = status == HTTPStatus.TOO_MANY_REQUESTS or (
            status == HTTPStatus.FORBIDDEN and (remaining == SPENT or bool(retry_after))
        )
        if limited:
            return RateLimited(self._reset(headers))
        if status == HTTPStatus.NOT_FOUND:
            return RepositoryNotFound()
        if status >= HTTPStatus.INTERNAL_SERVER_ERROR:
            return GitHubUnavailable()
        return RepositoryInaccessible()

    def _reset(self, headers: Any) -> int | None:
        """When the allowance returns, as seconds since the epoch; None if unsaid."""
        stated = _header(headers, RESET_HEADER)
        if stated.isdigit():
            return int(stated)
        wait = _header(headers, RETRY_AFTER_HEADER)
        if wait.isdigit():
            return int(self._clock()) + int(wait)
        return None


def first_page(address: RepositoryAddress) -> str:
    """The first page of a repository's releases."""
    owner = quote(address.owner, safe="")
    name = quote(address.name, safe="")
    return f"{API_ROOT}/repos/{owner}/{name}/releases?per_page={PAGE_SIZE}"


def next_page(link: str) -> str | None:
    """The next page a ``Link`` header names; None when it names none.

    A next page anywhere but on the API itself is refused rather than followed
    or ignored: following it would send a request somewhere nobody chose;
    ignoring it would import part of a history as though it were all of it.
    """
    found = NEXT_LINK.search(link)
    if found is None:
        return None
    url = found.group(1)
    if not url.startswith(f"{API_ROOT}/"):
        raise MalformedResponse("A next page away from GitHub's API")
    return url


def releases_in(payload: object) -> list[Release]:
    """The published releases on one page, drafts left out."""
    if not isinstance(payload, list):
        raise MalformedResponse("A page that is not a list of releases")
    found = []
    for entry in payload:
        release = _release(entry)
        if release is not None:
            found.append(release)
    return found


def _release(entry: object) -> Release | None:
    """One release; None for a draft; raises when the entry describes none.

    A malformed entry fails the page rather than being passed over, because an
    import missing one release without saying so misstates the history it is
    meant to hold.
    """
    if not isinstance(entry, dict):
        raise MalformedResponse("A release that is not an object")
    if entry.get(DRAFT_FIELD) is True:
        return None
    source_id = entry.get(ID_FIELD)
    prerelease = entry.get(PRERELEASE_FIELD, False)
    if not isinstance(source_id, int) or isinstance(source_id, bool):
        raise MalformedResponse("A release with no number")
    if not isinstance(prerelease, bool):
        raise MalformedResponse("A release that is neither pre-release nor not")
    try:
        return Release(
            source_id=source_id,
            tag=_text(entry.get(TAG_FIELD)),
            title=_text(entry.get(NAME_FIELD)),
            published_at=moment(entry.get(PUBLISHED_FIELD)),
            prerelease=prerelease,
            body=_text(entry.get(BODY_FIELD)),
            source_url=_text(entry.get(PAGE_FIELD)),
        )
    except InvalidRelease as error:
        raise MalformedResponse(str(error)) from error


def moment(value: object) -> str:
    """A GitHub timestamp in the one form the domain compares; empty if none."""
    if value is None:
        return ""
    if not isinstance(value, str):
        raise MalformedResponse("A date that is not text")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as error:
        raise MalformedResponse(f"Not a date: {value!r}") from error
    if parsed.tzinfo is None:
        # A moment with no zone is taken as UTC, which is what GitHub means.
        parsed = datetime.combine(parsed.date(), parsed.time(), UTC)
    return parsed.astimezone(UTC).strftime(MOMENT_FORMAT)


def _text(value: object) -> str:
    """A text field; empty for a missing one; raises for any other kind."""
    if value is None:
        return ""
    if not isinstance(value, str):
        raise MalformedResponse("A text field that is not text")
    return value


def _header(headers: Any, name: str) -> str:
    """One header's value, stripped; empty when there are no headers or no such."""
    if headers is None:
        return ""
    value = headers.get(name)
    return value.strip() if isinstance(value, str) else ""
