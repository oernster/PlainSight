"""The opener both of the application's own connections use.

The standard library's, with one change: a redirect is followed only while it
stays on the scheme, host and port the request was made to. GitHub redirects
within its API, for a renamed repository; a redirect anywhere else is not an
answer from the place that was asked, so it is refused before anything is sent
there.
"""

from __future__ import annotations

import urllib.error
import urllib.request
from typing import Any
from urllib.parse import urlsplit


class RedirectRefused(urllib.error.URLError):
    """A redirect that would have carried the request to another host."""


class _SameHostRedirects(urllib.request.HTTPRedirectHandler):
    """Follows a redirect only to the place the request was already going."""

    def redirect_request(
        self,
        req: urllib.request.Request,
        fp: Any,
        code: int,
        msg: str,
        headers: Any,
        newurl: str,
    ) -> urllib.request.Request | None:
        if _origin(newurl) != _origin(req.full_url):
            raise RedirectRefused(f"A redirect to another host was refused: {newurl}")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def open_on_same_host(request: urllib.request.Request, timeout: float) -> Any:
    """Open ``request``, following redirects only while they stay where it went.

    The opener is built per call rather than at import, since nothing in this
    package is constructed at import time.
    """
    opener = urllib.request.build_opener(_SameHostRedirects())
    return opener.open(request, timeout=timeout)


def _origin(url: str) -> tuple[str, str, int | None]:
    """Where an address goes: its scheme, its host and its port."""
    parts = urlsplit(url)
    return parts.scheme.lower(), (parts.hostname or "").lower(), parts.port
