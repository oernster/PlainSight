"""A redirect may not carry a request to another host.

Both of the application's own connections talk to GitHub's API; each opens
with the opener its source was built with by default. A redirect to the same
place is followed, which is how GitHub answers for a renamed repository; one to
anywhere else is refused before a byte is sent there.

Loopback only: two servers on 127.0.0.1, each on a port of its own, stand in
for the expected host and the one a redirect tries to reach.
"""

from __future__ import annotations

import threading
import urllib.error
import urllib.request
from collections.abc import Callable, Iterator
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from plainsight.application.release_import import MalformedResponse
from plainsight.domain.repository_address import RepositoryAddress
from plainsight.infrastructure.github_releases import GitHubReleaseHistory
from plainsight.infrastructure.same_host_opener import RedirectRefused
from plainsight.infrastructure.update_source import GitHubReleaseSource

LOOPBACK = "127.0.0.1"
ANY_FREE_PORT = 0
TIMEOUT_SECONDS = 5
FOUND = 302
OK = 200
BODY = b"{}"


class Server:
    """A loopback server that records each path asked of it."""

    def __init__(self, redirect_to: Callable[[str], str | None]) -> None:
        self.asked: list[str] = []
        recorded = self.asked

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                recorded.append(self.path)
                target = redirect_to(self.path)
                if target is None:
                    self.send_response(OK)
                    self.send_header("Content-Length", str(len(BODY)))
                    self.end_headers()
                    self.wfile.write(BODY)
                    return
                self.send_response(FOUND)
                self.send_header("Location", target)
                self.send_header("Content-Length", "0")
                self.end_headers()

            def log_message(self, *arguments: object) -> None:
                """Silent: a server log would read as a failure."""

        self._server = HTTPServer((LOOPBACK, ANY_FREE_PORT), Handler)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()

    def url(self, path: str) -> str:
        return f"http://{LOOPBACK}:{self._server.server_port}{path}"

    def stop(self) -> None:
        self._server.shutdown()
        self._server.server_close()
        self._thread.join()


@pytest.fixture
def elsewhere() -> Iterator[Server]:
    server = Server(lambda _path: None)
    yield server
    server.stop()


def default_openers() -> dict[str, Callable[..., object]]:
    return {
        "the update check": GitHubReleaseSource()._opener,
        "the release import": GitHubReleaseHistory()._opener,
    }


@pytest.mark.parametrize("which", sorted(default_openers()))
def test_a_redirect_to_another_host_is_refused(which: str, elsewhere: Server) -> None:
    home = Server(lambda _path: elsewhere.url("/stolen"))
    opener = default_openers()[which]
    try:
        with (
            pytest.raises(urllib.error.URLError),
            opener(
                urllib.request.Request(home.url("/start")), timeout=TIMEOUT_SECONDS
            ) as response,
        ):
            response.read()
    finally:
        home.stop()

    assert home.asked == ["/start"]
    assert elsewhere.asked == []


@pytest.mark.parametrize("which", sorted(default_openers()))
def test_a_redirect_on_the_same_host_is_followed(which: str) -> None:
    home = Server(lambda path: "/moved" if path == "/start" else None)
    opener = default_openers()[which]
    try:
        with opener(
            urllib.request.Request(home.url("/start")), timeout=TIMEOUT_SECONDS
        ) as response:
            body = response.read()
    finally:
        home.stop()

    assert body == BODY
    assert home.asked == ["/start", "/moved"]


def refusing_opener(request: object, timeout: float) -> object:
    raise RedirectRefused("A redirect to another host was refused")


def test_the_import_reports_a_refused_redirect_as_a_strange_answer() -> None:
    history = GitHubReleaseHistory(opener=refusing_opener)

    with pytest.raises(MalformedResponse):
        history.releases(RepositoryAddress("oernster", "PlainSight"), print, bool)


def test_the_update_check_treats_a_refused_redirect_as_no_answer() -> None:
    assert GitHubReleaseSource(opener=refusing_opener).latest_release() is None
