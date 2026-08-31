"""Whether a newer release exists, decided above the toolkit and the network.

Everything here is pure: a release arrives through the port as plain values and
this module says what to do about it. The comparison is dotted integers only, so
anything it cannot read compares as not newer; a malformed tag can never raise a
prompt.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass

from .ports import ReleaseSource

WINDOWS_KEY = "windows"
MACOS_KEY = "macos"
LINUX_KEY = "linux"

WINDOWS_PLATFORM = "win32"
MACOS_PLATFORM = "darwin"

# Which file each operating system is offered, matched on the name's ending.
ASSET_SUFFIXES = {
    WINDOWS_KEY: ".exe",
    MACOS_KEY: ".dmg",
    LINUX_KEY: ".flatpak",
}

TAG_PREFIX = "v"
COMPONENT_SEPARATOR = "."


@dataclass(frozen=True, slots=True)
class ReleaseAsset:
    """One downloadable file attached to a release."""

    name: str
    download_url: str


@dataclass(frozen=True, slots=True)
class ReleaseInfo:
    """A published release: its tag, its page and the files it carries."""

    version: str
    page_url: str
    assets: tuple[ReleaseAsset, ...] = ()


@dataclass(frozen=True, slots=True)
class UpdateStatus:
    """The answer to one check, in the terms the user interface reports.

    ``reachable`` is false only when the source could not be asked at all, which
    is the one outcome an automatic check stays silent about and a manual check
    has to say out loud.
    """

    current: str
    latest: str = ""
    update_available: bool = False
    download_url: str | None = None
    page_url: str | None = None
    reachable: bool = True


def version_components(tag: str) -> tuple[int, ...] | None:
    """This tag as dotted integers; None when it is not written that way."""
    text = tag.strip()
    if text[:1].lower() == TAG_PREFIX:
        text = text[1:]
    if not text:
        return None
    parts = text.split(COMPONENT_SEPARATOR)
    if not all(part.isdigit() for part in parts):
        return None
    return tuple(int(part) for part in parts)


def is_newer(latest: str, current: str) -> bool:
    """Whether ``latest`` names a later version than ``current``.

    Two tags of different lengths compare on the components they share, then on
    length, so 1.2 is older than 1.2.1 rather than equal to it.
    """
    there = version_components(latest)
    here = version_components(current)
    if there is None or here is None:
        return False
    return there > here


def platform_key_for(sys_platform: str) -> str:
    """The asset key for the operating system this string names."""
    if sys_platform.startswith(WINDOWS_PLATFORM):
        return WINDOWS_KEY
    if sys_platform.startswith(MACOS_PLATFORM):
        return MACOS_KEY
    return LINUX_KEY


def select_asset_url(assets: tuple[ReleaseAsset, ...], key: str) -> str | None:
    """The download for this platform; None when the release carries none."""
    suffix = ASSET_SUFFIXES.get(key)
    if suffix is None:
        return None
    for asset in assets:
        if asset.name.lower().endswith(suffix):
            return asset.download_url
    return None


@dataclass(frozen=True, slots=True)
class UpdateService:
    """Asks the source once and reports what it means."""

    source: ReleaseSource
    current_version: str
    platform_key: str

    def check(self, skipped_version: str = "") -> UpdateStatus:
        """What the latest release means for the version running now.

        ``skipped_version`` silences one exact tag. Both sides of that
        comparison come from the same endpoint, so string equality is the whole
        of it; an automatic check passes the remembered tag in and a manual one
        passes nothing, which is how the same code answers both.
        """
        release = self.source.latest_release()
        if release is None:
            return UpdateStatus(current=self.current_version, reachable=False)
        available = is_newer(release.version, self.current_version)
        if available and release.version == skipped_version:
            available = False
        return UpdateStatus(
            current=self.current_version,
            latest=release.version,
            update_available=available,
            download_url=select_asset_url(release.assets, self.platform_key),
            page_url=release.page_url,
        )


class UpdateOutcome(enum.Enum):
    """What a finished check should say, if anything."""

    SILENT = "silent"
    PROMPT = "prompt"
    UP_TO_DATE = "up_to_date"
    UNREACHABLE = "unreachable"


def outcome_for(status: UpdateStatus, manual: bool) -> UpdateOutcome:
    """What to report for this result.

    A check the user asked for reports every outcome, including the two that
    are good news. A check nobody asked for speaks only when there is something
    to download, so an unreachable source or an up to date installation passes
    without a word.
    """
    if status.update_available:
        return UpdateOutcome.PROMPT
    if not manual:
        return UpdateOutcome.SILENT
    return UpdateOutcome.UP_TO_DATE if status.reachable else UpdateOutcome.UNREACHABLE
