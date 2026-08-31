"""Which conversation the setup program is having.

One reading of the machine decides everything the window then shows: the
screen, its heading, the options on it and the buttons under it. Deciding it
once, here, is what stops those four drifting apart.

Pure, so every state can be asserted in a test rather than read off a
screenshot.
"""

from __future__ import annotations

import enum

NUMERIC_PARTS = 4
NO_PART = 0


class Route(enum.Enum):
    """The five states setup can be run in."""

    INSTALL = "install"
    UPDATE = "update"
    DOWNGRADE = "downgrade"
    MANAGE = "manage"
    UNINSTALL = "uninstall"


def version_key(version: str) -> tuple[int, ...]:
    """A version as numbers, so two of them can be compared.

    Anything that is not a digit is dropped from each dotted part, so a
    pre-release suffix orders with the release it belongs to rather than
    raising.
    """
    parts = []
    for part in version.split("."):
        digits = "".join(character for character in part if character.isdigit())
        parts.append(int(digits) if digits else NO_PART)
    parts.extend([NO_PART] * (NUMERIC_PARTS - len(parts)))
    return tuple(parts[:NUMERIC_PARTS])


def route_for(installed: str, version: str, uninstalling: bool) -> Route:
    """Which route this run takes, from what is recorded as installed.

    Being asked to uninstall settles it before anything else is considered,
    because that is the one route the user names rather than setup deducing.
    """
    if uninstalling:
        return Route.UNINSTALL
    if not installed:
        return Route.INSTALL
    here, arriving = version_key(installed), version_key(version)
    if here < arriving:
        return Route.UPDATE
    if here > arriving:
        return Route.DOWNGRADE
    return Route.MANAGE
