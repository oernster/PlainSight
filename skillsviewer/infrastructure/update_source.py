"""The one place the application opens a connection of its own.

It asks GitHub for the latest published release of this repository and nothing
else. The endpoint returns only a published, non-draft, non-prerelease release,
so a tag pushed mid-development is invisible here by the endpoint's own
contract rather than by a check made after the fact.

Every failure is answered with None. There are no retries: a check that could
not be made is simply not made; the next one happens a day later.
"""

from __future__ import annotations

import json
import urllib.request
from collections.abc import Callable
from typing import Any

from ..application.update import ReleaseAsset, ReleaseInfo

RELEASE_URL = "https://api.github.com/repos/oernster/SkillsViewer/releases/latest"
ACCEPT_HEADER = "application/vnd.github+json"
TIMEOUT_SECONDS = 5

TAG_FIELD = "tag_name"
PAGE_FIELD = "html_url"
ASSETS_FIELD = "assets"
ASSET_NAME_FIELD = "name"
ASSET_URL_FIELD = "browser_download_url"

Opener = Callable[..., Any]


class GitHubReleaseSource:
    """The latest release, read from the GitHub releases endpoint."""

    def __init__(self, opener: Opener | None = None) -> None:
        # The opener is injected so a test never reaches the network; the
        # default is the standard library, so nothing is added to ship this.
        self._opener = urllib.request.urlopen if opener is None else opener

    def latest_release(self) -> ReleaseInfo | None:
        """The newest published release; None when it could not be read."""
        try:
            payload = self._fetch()
        except (OSError, ValueError):
            return None
        return _release(payload)

    def _fetch(self) -> object:
        """The endpoint's answer, decoded. Raises when anything goes wrong."""
        request = urllib.request.Request(RELEASE_URL, headers={"Accept": ACCEPT_HEADER})
        with self._opener(request, timeout=TIMEOUT_SECONDS) as response:
            return json.loads(response.read().decode("utf-8"))


def _release(payload: object) -> ReleaseInfo | None:
    """A release from a decoded body; None when the body cannot describe one.

    Every field is checked before it is used. A body of the right shape with a
    field of the wrong type is a body this cannot read, which is the same
    outcome as no body at all.
    """
    if not isinstance(payload, dict):
        return None
    tag = payload.get(TAG_FIELD)
    page = payload.get(PAGE_FIELD)
    if not isinstance(tag, str) or not tag.strip():
        return None
    if not isinstance(page, str) or not page.strip():
        return None
    return ReleaseInfo(
        version=tag, page_url=page, assets=_assets(payload.get(ASSETS_FIELD))
    )


def _assets(value: object) -> tuple[ReleaseAsset, ...]:
    """The downloadable files listed; malformed entries are left out."""
    if not isinstance(value, list):
        return ()
    found = []
    for entry in value:
        asset = _asset(entry)
        if asset is not None:
            found.append(asset)
    return tuple(found)


def _asset(entry: object) -> ReleaseAsset | None:
    """One downloadable file; None when the entry does not describe one."""
    if not isinstance(entry, dict):
        return None
    name = entry.get(ASSET_NAME_FIELD)
    address = entry.get(ASSET_URL_FIELD)
    if not isinstance(name, str) or not isinstance(address, str):
        return None
    if not name.strip() or not address.strip():
        return None
    return ReleaseAsset(name=name, download_url=address)
