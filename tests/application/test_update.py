"""The update decision: what a release means for the version running now."""

from __future__ import annotations

import pytest

from skillsviewer.application.update import (
    LINUX_KEY,
    MACOS_KEY,
    WINDOWS_KEY,
    ReleaseAsset,
    ReleaseInfo,
    UpdateOutcome,
    UpdateService,
    UpdateStatus,
    is_newer,
    outcome_for,
    platform_key_for,
    select_asset_url,
    version_components,
)

CURRENT = "0.1.0"


class FakeSource:
    """A release source that answers whatever the test hands it."""

    def __init__(self, release: ReleaseInfo | None) -> None:
        self._release = release
        self.asked = 0

    def latest_release(self) -> ReleaseInfo | None:
        self.asked += 1
        return self._release


def a_release(version: str, assets: tuple[ReleaseAsset, ...] = ()) -> ReleaseInfo:
    return ReleaseInfo(
        version=version, page_url="https://example.test/releases", assets=assets
    )


def a_service(release: ReleaseInfo | None, key: str = WINDOWS_KEY) -> UpdateService:
    return UpdateService(
        source=FakeSource(release), current_version=CURRENT, platform_key=key
    )


@pytest.mark.parametrize(
    ("tag", "expected"),
    [
        ("1.2.3", (1, 2, 3)),
        ("v1.2.3", (1, 2, 3)),
        ("V1.2.3", (1, 2, 3)),
        ("  1.2.3  ", (1, 2, 3)),
        ("1.2.3.4", (1, 2, 3, 4)),
        ("2", (2,)),
        ("", None),
        ("v", None),
        ("1.2.3-beta", None),
        ("latest", None),
        ("1..2", None),
    ],
)
def test_a_tag_reads_as_dotted_integers_or_not_at_all(
    tag: str, expected: tuple[int, ...] | None
) -> None:
    assert version_components(tag) == expected


@pytest.mark.parametrize(
    ("latest", "current", "expected"),
    [
        ("0.2.0", "0.1.0", True),
        ("v0.2.0", "0.1.0", True),
        ("0.1.0", "0.1.0", False),
        ("0.0.9", "0.1.0", False),
        ("0.1.1", "0.1", True),
        ("0.1", "0.1.1", False),
        ("0.2.0-rc1", "0.1.0", False),
        ("0.2.0", "not a version", False),
        ("nonsense", "rubbish", False),
    ],
)
def test_newer_is_decided_on_numbers_only(
    latest: str, current: str, expected: bool
) -> None:
    assert is_newer(latest, current) is expected


@pytest.mark.parametrize(
    ("reported", "expected"),
    [
        ("win32", WINDOWS_KEY),
        ("darwin", MACOS_KEY),
        ("linux", LINUX_KEY),
        ("freebsd14", LINUX_KEY),
        ("", LINUX_KEY),
    ],
)
def test_each_operating_system_maps_to_its_own_file(
    reported: str, expected: str
) -> None:
    assert platform_key_for(reported) == expected


def test_the_asset_for_this_platform_is_picked_by_its_ending() -> None:
    assets = (
        ReleaseAsset(name="SkillsViewer.flatpak", download_url="linux"),
        ReleaseAsset(name="SkillsViewerSetup.EXE", download_url="windows"),
        ReleaseAsset(name="SkillsViewer.dmg", download_url="macos"),
    )

    assert select_asset_url(assets, WINDOWS_KEY) == "windows"
    assert select_asset_url(assets, MACOS_KEY) == "macos"
    assert select_asset_url(assets, LINUX_KEY) == "linux"


def test_a_release_carrying_nothing_for_this_platform_offers_no_file() -> None:
    assets = (ReleaseAsset(name="notes.txt", download_url="text"),)

    assert select_asset_url(assets, WINDOWS_KEY) is None
    assert select_asset_url((), WINDOWS_KEY) is None


def test_a_platform_nobody_ships_for_offers_no_file() -> None:
    assets = (ReleaseAsset(name="SkillsViewerSetup.exe", download_url="windows"),)

    assert select_asset_url(assets, "solaris") is None


def test_an_unreachable_source_is_reported_as_unreachable() -> None:
    status = a_service(None).check()

    assert status == UpdateStatus(current=CURRENT, reachable=False)
    assert status.update_available is False


def test_a_newer_release_is_available_with_its_file_and_its_page() -> None:
    asset = ReleaseAsset(name="SkillsViewerSetup.exe", download_url="the-file")

    status = a_service(a_release("0.2.0", (asset,))).check()

    assert status.update_available is True
    assert status.latest == "0.2.0"
    assert status.current == CURRENT
    assert status.download_url == "the-file"
    assert status.page_url == "https://example.test/releases"
    assert status.reachable is True


def test_the_running_version_is_not_an_update() -> None:
    status = a_service(a_release(CURRENT)).check()

    assert status.update_available is False
    assert status.reachable is True


def test_a_release_with_no_file_for_this_platform_still_offers_the_page() -> None:
    status = a_service(a_release("0.2.0")).check()

    assert status.update_available is True
    assert status.download_url is None
    assert status.page_url == "https://example.test/releases"


def test_a_skipped_release_is_seen_but_not_offered() -> None:
    status = a_service(a_release("0.2.0")).check(skipped_version="0.2.0")

    assert status.latest == "0.2.0"
    assert status.update_available is False


def test_skipping_one_release_does_not_silence_the_next() -> None:
    status = a_service(a_release("0.3.0")).check(skipped_version="0.2.0")

    assert status.update_available is True


def test_the_source_is_asked_exactly_once_per_check() -> None:
    source = FakeSource(a_release("0.2.0"))
    service = UpdateService(
        source=source, current_version=CURRENT, platform_key=WINDOWS_KEY
    )

    service.check()

    assert source.asked == 1


@pytest.mark.parametrize(
    ("status", "manual", "expected"),
    [
        (
            UpdateStatus(current=CURRENT, latest="0.2.0", update_available=True),
            False,
            UpdateOutcome.PROMPT,
        ),
        (
            UpdateStatus(current=CURRENT, latest="0.2.0", update_available=True),
            True,
            UpdateOutcome.PROMPT,
        ),
        (UpdateStatus(current=CURRENT, latest=CURRENT), False, UpdateOutcome.SILENT),
        (
            UpdateStatus(current=CURRENT, reachable=False),
            False,
            UpdateOutcome.SILENT,
        ),
        (
            UpdateStatus(current=CURRENT, latest=CURRENT),
            True,
            UpdateOutcome.UP_TO_DATE,
        ),
        (
            UpdateStatus(current=CURRENT, reachable=False),
            True,
            UpdateOutcome.UNREACHABLE,
        ),
    ],
)
def test_only_a_check_the_user_asked_for_reports_good_news(
    status: UpdateStatus, manual: bool, expected: UpdateOutcome
) -> None:
    assert outcome_for(status, manual) is expected
