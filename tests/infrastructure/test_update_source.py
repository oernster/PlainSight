"""The GitHub adapter, asked through a fake opener so no test leaves the machine."""

from __future__ import annotations

import json
from typing import Any, Self

import pytest

from plainsight.application.update import ReleaseAsset
from plainsight.infrastructure.update_source import (
    ACCEPT_HEADER,
    RELEASE_URL,
    TIMEOUT_SECONDS,
    GitHubReleaseSource,
)

A_BODY = {
    "tag_name": "v0.2.0",
    "html_url": "https://github.com/oernster/PlainSight/releases/tag/v0.2.0",
    "assets": [
        {"name": "PlainSightSetup.exe", "browser_download_url": "the-exe"},
        {"name": "PlainSight.dmg", "browser_download_url": "the-dmg"},
    ],
}


class FakeResponse:
    """What urlopen hands back: a context manager over some bytes."""

    def __init__(self, payload: bytes) -> None:
        self._payload = payload

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_unused: object) -> bool:
        return False

    def read(self) -> bytes:
        return self._payload


class FakeOpener:
    """Records the request it was given and answers with a fixed body."""

    def __init__(
        self, payload: object = A_BODY, raises: Exception | None = None
    ) -> None:
        self._payload = payload
        self._raises = raises
        self.request: Any = None
        self.timeout: Any = None

    def __call__(self, request: Any, timeout: Any = None) -> FakeResponse:
        self.request = request
        self.timeout = timeout
        if self._raises is not None:
            raise self._raises
        if isinstance(self._payload, bytes):
            return FakeResponse(self._payload)
        return FakeResponse(json.dumps(self._payload).encode("utf-8"))


def test_a_published_release_is_read_with_its_page_and_its_files() -> None:
    release = GitHubReleaseSource(FakeOpener()).latest_release()

    assert release is not None
    assert release.version == "v0.2.0"
    assert release.page_url == A_BODY["html_url"]
    assert release.assets == (
        ReleaseAsset(name="PlainSightSetup.exe", download_url="the-exe"),
        ReleaseAsset(name="PlainSight.dmg", download_url="the-dmg"),
    )


def test_it_asks_this_repository_and_nothing_else() -> None:
    opener = FakeOpener()

    GitHubReleaseSource(opener).latest_release()

    assert opener.request.full_url == RELEASE_URL
    assert opener.request.get_header("Accept") == ACCEPT_HEADER
    assert opener.timeout == TIMEOUT_SECONDS


def test_the_default_opener_is_the_standard_library() -> None:
    """Constructed with nothing, it still has something to ask through."""
    import urllib.request

    source = GitHubReleaseSource()

    assert source._opener is urllib.request.urlopen


@pytest.mark.parametrize(
    "failure",
    [OSError("no route to host"), ValueError("not json")],
)
def test_a_source_that_cannot_be_asked_answers_nothing(failure: Exception) -> None:
    assert GitHubReleaseSource(FakeOpener(raises=failure)).latest_release() is None


def test_a_body_that_is_not_json_answers_nothing() -> None:
    assert GitHubReleaseSource(FakeOpener(payload=b"<html>")).latest_release() is None


@pytest.mark.parametrize(
    "payload",
    [
        [],
        "a string",
        {"html_url": "https://example.test"},
        {"tag_name": "", "html_url": "https://example.test"},
        {"tag_name": "   ", "html_url": "https://example.test"},
        {"tag_name": 2, "html_url": "https://example.test"},
        {"tag_name": "v1.0.0"},
        {"tag_name": "v1.0.0", "html_url": ""},
        {"tag_name": "v1.0.0", "html_url": 7},
    ],
)
def test_a_body_that_cannot_describe_a_release_answers_nothing(payload: object) -> None:
    assert GitHubReleaseSource(FakeOpener(payload=payload)).latest_release() is None


@pytest.mark.parametrize("assets", [None, "not a list", 3])
def test_a_release_whose_files_make_no_sense_still_reads_as_a_release(
    assets: object,
) -> None:
    payload = {
        "tag_name": "v1.0.0",
        "html_url": "https://example.test",
        "assets": assets,
    }

    release = GitHubReleaseSource(FakeOpener(payload=payload)).latest_release()

    assert release is not None
    assert release.assets == ()


def test_a_malformed_file_entry_is_left_out_rather_than_read_wrongly() -> None:
    payload = {
        "tag_name": "v1.0.0",
        "html_url": "https://example.test",
        "assets": [
            "not a mapping",
            {"name": "good.exe", "browser_download_url": "the-exe"},
            {"name": "no url"},
            {"browser_download_url": "no name"},
            {"name": 5, "browser_download_url": "the-exe"},
            {"name": "blank.exe", "browser_download_url": "  "},
            {"name": "  ", "browser_download_url": "the-exe"},
        ],
    }

    release = GitHubReleaseSource(FakeOpener(payload=payload)).latest_release()

    assert release is not None
    assert release.assets == (ReleaseAsset(name="good.exe", download_url="the-exe"),)
