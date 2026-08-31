"""The route and everything it says, asserted rather than screenshotted."""

from __future__ import annotations

import pytest

from installer.route import Route, route_for, version_key
from installer.wording import (
    FLOW_ARROW,
    verdict_line,
    verdict_title,
    version_line,
    wording_for,
)

THIS_VERSION = "1.2.0"


def test_nothing_recorded_is_an_install() -> None:
    assert route_for("", THIS_VERSION, uninstalling=False) is Route.INSTALL


def test_an_older_recorded_version_is_an_update() -> None:
    assert route_for("1.1.0", THIS_VERSION, uninstalling=False) is Route.UPDATE


def test_a_newer_recorded_version_is_a_downgrade() -> None:
    assert route_for("1.3.0", THIS_VERSION, uninstalling=False) is Route.DOWNGRADE


def test_the_same_version_leaves_nothing_to_install() -> None:
    assert route_for(THIS_VERSION, THIS_VERSION, uninstalling=False) is Route.MANAGE


def test_being_asked_to_uninstall_settles_it_first() -> None:
    """Whatever is recorded, the route the user named wins."""
    for installed in ("", "1.1.0", THIS_VERSION, "9.9.9"):
        assert route_for(installed, THIS_VERSION, uninstalling=True) is Route.UNINSTALL


@pytest.mark.parametrize(
    "version, expected",
    [
        ("1.2.0", (1, 2, 0, 0)),
        ("1.2.0.4", (1, 2, 0, 4)),
        ("1.2.0-rc1", (1, 2, 1, 0)),
        ("", (0, 0, 0, 0)),
        ("1.2.0.4.5", (1, 2, 0, 4)),
    ],
)
def test_a_version_reads_as_four_numbers(version: str, expected: tuple) -> None:
    assert version_key(version) == expected


def test_a_prerelease_orders_beside_its_release_rather_than_raising() -> None:
    assert version_key("1.2.0") < version_key("1.3.0-rc1")


def test_every_route_says_something() -> None:
    for route in Route:
        wording = wording_for(route)
        assert wording.heading and wording.lead and wording.go_ahead


def test_neither_two_version_route_names_a_version_in_its_heading() -> None:
    """A heading is where a single version belongs, so these name none."""
    for route in (Route.UPDATE, Route.DOWNGRADE):
        assert "1." not in wording_for(route).heading


def test_two_version_routes_show_the_flow_beneath_the_heading() -> None:
    for route in (Route.UPDATE, Route.DOWNGRADE):
        line = version_line(route, "1.1.0", THIS_VERSION)
        assert FLOW_ARROW in line
        assert "1.1.0" in line
        assert THIS_VERSION in line


def test_a_one_version_route_names_the_one_version() -> None:
    assert version_line(Route.INSTALL, "", THIS_VERSION) == f"v{THIS_VERSION}"
    assert version_line(Route.MANAGE, THIS_VERSION, THIS_VERSION) == f"v{THIS_VERSION}"
    assert version_line(Route.UNINSTALL, "1.1.0", THIS_VERSION) == "v1.1.0"


def test_the_verdict_is_named_for_what_was_attempted() -> None:
    assert "removed" in verdict_title(Route.UNINSTALL, succeeded=True)
    assert "updated" in verdict_title(Route.UPDATE, succeeded=True)
    assert "put back" in verdict_title(Route.DOWNGRADE, succeeded=True)
    assert "installed" in verdict_title(Route.INSTALL, succeeded=True)
    assert "installed" in verdict_title(Route.MANAGE, succeeded=True)


def test_a_failure_says_so_whatever_was_attempted() -> None:
    for route in Route:
        assert verdict_title(route, succeeded=False) == "Setup did not finish"


def test_a_failure_names_where_its_log_went() -> None:
    line = verdict_line(succeeded=False, log_path="C:/temp/setup.log")

    assert "C:/temp/setup.log" in line


def test_a_success_does_not_mention_a_log() -> None:
    assert "log" not in verdict_line(succeeded=True, log_path="C:/temp/setup.log")
