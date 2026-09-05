"""Everything the setup program says.

Pure, so every state is a test rather than a screenshot. The heading is where a
SINGLE version belongs: an update and a downgrade are about two versions, so
neither names one there. Both appear in the flow line beneath it instead.
"""

from __future__ import annotations

from dataclasses import dataclass

from installer.route import Route

PRODUCT = "PlainSight"
TAGLINE = "A reader for your documents"
FLOW_ARROW = "→"


@dataclass(frozen=True, slots=True)
class Wording:
    """What one route says: its heading, its lead and its go-ahead."""

    heading: str
    lead: str
    go_ahead: str


_WORDING = {
    Route.INSTALL: Wording(
        heading=f"Install {PRODUCT}",
        lead=(
            "It goes in your own account, so Windows will not ask for an "
            "administrator. Nothing outside your profile is touched."
        ),
        go_ahead="Install",
    ),
    Route.UPDATE: Wording(
        heading=f"Update {PRODUCT}",
        lead="Your settings and your chosen skills folder are kept.",
        go_ahead="Update",
    ),
    Route.DOWNGRADE: Wording(
        heading=f"Go back to an earlier {PRODUCT}",
        lead=(
            "A newer version is installed than the one this setup carries. "
            "Going back replaces it with the older one."
        ),
        go_ahead="Go back",
    ),
    Route.MANAGE: Wording(
        heading=f"{PRODUCT} is installed",
        lead=(
            "This is the version already here. Repair puts the files back and "
            "leaves everything else alone; reinstall writes them again with "
            "the choices on this screen."
        ),
        go_ahead="Repair",
    ),
    Route.UNINSTALL: Wording(
        heading=f"Remove {PRODUCT}",
        lead=(
            "The application and its shortcuts are removed. Your settings and "
            "your skills themselves are left where they are."
        ),
        go_ahead="Uninstall",
    ),
}


def wording_for(route: Route) -> Wording:
    """What this route says."""
    return _WORDING[route]


def version_line(route: Route, installed: str, arriving: str) -> str:
    """The sentence beneath the heading naming the versions in play."""
    if route in (Route.UPDATE, Route.DOWNGRADE):
        return f"v{installed}  {FLOW_ARROW}  v{arriving}"
    if route in (Route.MANAGE, Route.UNINSTALL):
        return f"v{installed}"
    return f"v{arriving}"


def verdict_title(route: Route, succeeded: bool) -> str:
    """How it ended, named for what was being attempted."""
    if not succeeded:
        return "Setup did not finish"
    if route is Route.UNINSTALL:
        return f"{PRODUCT} was removed"
    if route is Route.UPDATE:
        return f"{PRODUCT} was updated"
    if route is Route.DOWNGRADE:
        return f"{PRODUCT} was put back"
    return f"{PRODUCT} is installed"


def verdict_line(succeeded: bool, log_path: str) -> str:
    """One line under the verdict; a failure names where its log went."""
    if succeeded:
        return "You can close this window."
    return f"Nothing was left half done. The step log is at {log_path}"
