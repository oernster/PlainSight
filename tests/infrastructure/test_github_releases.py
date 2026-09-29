"""The GitHub releases client, asked through a fake opener: nothing leaves here."""

from __future__ import annotations

import http.client
import json
import urllib.error
from typing import Any, Self

import pytest

from plainsight.application.release_import import (
    GitHubUnavailable,
    ImportCancelled,
    MalformedResponse,
    NetworkUnavailable,
    RateLimited,
    RepositoryInaccessible,
    RepositoryNotFound,
    TimedOut,
)
from plainsight.domain.repository_address import RepositoryAddress
from plainsight.infrastructure import github_releases
from plainsight.infrastructure.github_releases import (
    HEADERS,
    MAX_PAGES,
    TIMEOUT_SECONDS,
    GitHubReleaseHistory,
    first_page,
    moment,
)

ADDRESS = RepositoryAddress("oernster", "PlainSight")
FIRST = "https://api.github.com/repos/oernster/PlainSight/releases?per_page=100"
SECOND = FIRST + "&page=2"
THIRD = FIRST + "&page=3"


def release(number: int, **changes: object) -> dict[str, object]:
    entry: dict[str, object] = {
        "id": number,
        "tag_name": f"v{number}.0",
        "name": f"Release {number}",
        "published_at": "2026-09-29T10:15:00Z",
        "draft": False,
        "prerelease": False,
        "body": f"Notes {number}",
        "html_url": f"https://github.com/oernster/PlainSight/releases/tag/v{number}.0",
    }
    entry.update(changes)
    return entry


def link_to(url: str) -> str:
    return f'<{url}>; rel="next", <{THIRD}>; rel="last"'


class FakeResponse:
    """What urlopen hands back: a context manager over bytes and headers."""

    def __init__(self, payload: bytes, headers: dict[str, str]) -> None:
        self._payload = payload
        self.headers = headers
        self.asked_for: int | None = None

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_unused: object) -> bool:
        return False

    def read(self, size: int) -> bytes:
        self.asked_for = size
        return self._payload


class PagedOpener:
    """Answers each address from a table of pages; records every request."""

    def __init__(self, pages: dict[str, tuple[object, str]]) -> None:
        self.pages = pages
        self.requests: list[Any] = []
        self.timeouts: list[Any] = []
        self.last: FakeResponse | None = None

    def __call__(self, request: Any, timeout: Any = None) -> FakeResponse:
        self.requests.append(request)
        self.timeouts.append(timeout)
        payload, link = self.pages[request.full_url]
        body = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
        self.last = FakeResponse(body, {"Link": link} if link else {})
        return self.last


class RaisingOpener:
    """Raises the one error it was given."""

    def __init__(self, error: BaseException) -> None:
        self.error = error

    def __call__(self, request: Any, timeout: Any = None) -> FakeResponse:
        raise self.error


def fetch(opener: Any, clock: Any = None) -> tuple[Any, list[int]]:
    counts: list[int] = []
    found = GitHubReleaseHistory(opener, clock).releases(
        ADDRESS, counts.append, lambda: False
    )
    return found, counts


def refusal(code: int, headers: dict[str, str] | None = None) -> Exception:
    """A refusal from GitHub, as urlopen raises one."""
    stated: Any = headers
    return urllib.error.HTTPError(FIRST, code, "refused", stated, None)


def test_the_first_page_asks_for_as_many_releases_as_github_allows() -> None:
    assert first_page(ADDRESS) == FIRST


def test_one_page_is_read_with_the_right_headers_and_timeout() -> None:
    opener = PagedOpener({FIRST: ([release(1), release(2)], "")})

    found, counts = fetch(opener)

    assert [one.source_id for one in found] == [1, 2]
    assert counts == [2]
    assert opener.timeouts == [TIMEOUT_SECONDS]
    request = opener.requests[0]
    for name, value in HEADERS.items():
        assert request.get_header(name.capitalize()) == value


def test_every_page_is_followed_until_there_is_no_next() -> None:
    opener = PagedOpener(
        {
            FIRST: ([release(1), release(2)], link_to(SECOND)),
            SECOND: ([release(3)], link_to(THIRD)),
            THIRD: ([release(4)], ""),
        }
    )

    found, counts = fetch(opener)

    assert [one.source_id for one in found] == [1, 2, 3, 4]
    assert [request.full_url for request in opener.requests] == [FIRST, SECOND, THIRD]
    assert counts == [2, 3, 4]


def test_an_empty_list_is_no_releases() -> None:
    found, _counts = fetch(PagedOpener({FIRST: ([], "")}))

    assert found == ()


def test_drafts_are_left_out_and_prereleases_kept() -> None:
    opener = PagedOpener(
        {FIRST: ([release(1, draft=True), release(2, prerelease=True)], "")}
    )

    found, _counts = fetch(opener)

    assert [(one.source_id, one.prerelease) for one in found] == [(2, True)]


def test_missing_title_body_and_date_become_empty_rather_than_failing() -> None:
    opener = PagedOpener(
        {FIRST: ([release(1, name=None, body=None, published_at=None)], "")}
    )

    (only,), _counts = fetch(opener)

    assert (only.title, only.body, only.published_at) == ("", "", "")


def test_a_next_page_away_from_the_api_is_refused() -> None:
    opener = PagedOpener({FIRST: ([release(1)], link_to("https://evil.example/x"))})

    with pytest.raises(MalformedResponse):
        fetch(opener)


def test_a_pagination_loop_is_stopped() -> None:
    opener = PagedOpener({FIRST: ([release(1)], link_to(FIRST))})

    with pytest.raises(MalformedResponse):
        fetch(opener)

    assert len(opener.requests) == MAX_PAGES


def test_a_stop_asked_for_is_honoured_before_the_next_request() -> None:
    opener = PagedOpener({FIRST: ([release(1)], "")})

    with pytest.raises(ImportCancelled):
        GitHubReleaseHistory(opener).releases(ADDRESS, lambda _n: None, lambda: True)

    assert opener.requests == []


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (refusal(404), RepositoryNotFound),
        (refusal(401), RepositoryInaccessible),
        (refusal(403), RepositoryInaccessible),
        (refusal(451), RepositoryInaccessible),
        (refusal(500), GitHubUnavailable),
        (refusal(503), GitHubUnavailable),
        (urllib.error.URLError(TimeoutError()), TimedOut),
        (urllib.error.URLError("no route to host"), NetworkUnavailable),
        (TimeoutError(), TimedOut),
        (ConnectionResetError(), NetworkUnavailable),
        (http.client.IncompleteRead(b""), NetworkUnavailable),
    ],
)
def test_each_failure_is_raised_as_the_problem_it_is(
    error: BaseException, expected: type
) -> None:
    with pytest.raises(expected):
        fetch(RaisingOpener(error))


def test_a_spent_allowance_says_when_it_returns() -> None:
    error = refusal(403, {"X-RateLimit-Remaining": "0", "X-RateLimit-Reset": "1790"})

    with pytest.raises(RateLimited) as limited:
        fetch(RaisingOpener(error))

    assert limited.value.reset_epoch == 1790


def test_too_many_requests_counts_from_now_when_only_a_wait_is_given() -> None:
    error = refusal(429, {"Retry-After": "60"})

    with pytest.raises(RateLimited) as limited:
        fetch(RaisingOpener(error), clock=lambda: 1000.5)

    assert limited.value.reset_epoch == 1060


def test_a_limit_that_says_nothing_of_when_still_says_it_is_a_limit() -> None:
    error = refusal(429, {"Retry-After": "soon"})

    with pytest.raises(RateLimited) as limited:
        fetch(RaisingOpener(error))

    assert limited.value.reset_epoch is None


def test_a_page_past_the_cap_is_refused_unread(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(github_releases, "MAX_PAGE_BYTES", 8)
    opener = PagedOpener({FIRST: (b"[" + b" " * 20 + b"]", "")})

    with pytest.raises(MalformedResponse):
        fetch(opener)

    assert opener.last is not None and opener.last.asked_for == 9


@pytest.mark.parametrize(
    "payload",
    [
        b"not json",
        b"\xff\xfe",
        {"message": "a page that is an object"},
        ["a release that is text"],
        [release(1, id=None)],
        [release(1, id=True)],
        [release(1, prerelease="yes")],
        [release(1, tag_name="")],
        [release(1, tag_name=None)],
        [release(1, name=7)],
        [release(1, published_at="yesterday")],
        [release(1, published_at=20260929)],
    ],
)
def test_a_body_that_does_not_describe_releases_is_refused(payload: object) -> None:
    with pytest.raises(MalformedResponse):
        fetch(PagedOpener({FIRST: (payload, "")}))


@pytest.mark.parametrize(
    ("stated", "normalised"),
    [
        ("2026-09-29T10:15:00Z", "2026-09-29T10:15:00Z"),
        ("2026-09-29T11:15:00+01:00", "2026-09-29T10:15:00Z"),
        ("2026-09-29T10:15:00", "2026-09-29T10:15:00Z"),
        ("2026-09-29T10:15:00.987Z", "2026-09-29T10:15:00Z"),
        (None, ""),
    ],
)
def test_every_moment_arrives_in_the_one_form_the_domain_compares(
    stated: object, normalised: str
) -> None:
    assert moment(stated) == normalised
