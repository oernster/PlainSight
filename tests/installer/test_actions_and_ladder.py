"""What an install does: the fence on the archive, then the weighted ladder."""

from __future__ import annotations

import pathlib
import zipfile

import pytest

from installer.actions import (
    ExtractionEscape,
    extract_payload,
    install_size_kb,
    remove_tree,
    safe_members,
)
from installer.performing import (
    COMPLETE_PERCENT,
    EXTRACT_WEIGHT,
    Step,
    install_steps,
    ladder,
    uninstall_steps,
)
from installer.plan import InstallPlan
from installer.steplog import StepLog

A_FILE = "SkillsViewer.exe"
SOME_CONTENT = b"x" * 4096


def an_archive(tmp_path: pathlib.Path, names: tuple[str, ...]) -> pathlib.Path:
    path = tmp_path / "payload.zip"
    with zipfile.ZipFile(path, "w") as archive:
        for name in names:
            archive.writestr(name, SOME_CONTENT)
    return path


def test_a_plain_archive_unpacks(tmp_path: pathlib.Path) -> None:
    archive = an_archive(tmp_path, (A_FILE, "assets/icon.png"))
    target = tmp_path / "install"

    extract_payload(archive, target)

    assert (target / A_FILE).is_file()
    assert (target / "assets" / "icon.png").is_file()


def test_an_entry_climbing_out_is_refused(tmp_path: pathlib.Path) -> None:
    archive = an_archive(tmp_path, (A_FILE, "../escaped.txt"))
    target = tmp_path / "install"

    with pytest.raises(ExtractionEscape):
        extract_payload(archive, target)


def test_the_whole_archive_is_checked_before_any_of_it_is_written(
    tmp_path: pathlib.Path,
) -> None:
    """A crafted archive cannot write half its entries before one is caught."""
    archive = an_archive(tmp_path, (A_FILE, "../escaped.txt"))
    target = tmp_path / "install"

    with pytest.raises(ExtractionEscape):
        extract_payload(archive, target)

    assert not (target / A_FILE).exists()
    assert not (tmp_path / "escaped.txt").exists()


def test_the_members_of_a_safe_archive_are_all_returned(
    tmp_path: pathlib.Path,
) -> None:
    archive = an_archive(tmp_path, (A_FILE, "assets/icon.png"))
    target = tmp_path / "install"
    target.mkdir()

    with zipfile.ZipFile(archive) as opened:
        assert sorted(safe_members(opened, target)) == [
            "SkillsViewer.exe",
            "assets/icon.png",
        ]


def test_the_installed_size_is_reported_in_kilobytes(tmp_path: pathlib.Path) -> None:
    target = tmp_path / "install"
    target.mkdir()
    (target / A_FILE).write_bytes(SOME_CONTENT)

    assert install_size_kb(target) == len(SOME_CONTENT) // 1024


def test_a_directory_that_is_not_there_has_no_size(tmp_path: pathlib.Path) -> None:
    assert install_size_kb(tmp_path / "absent") == 0


def test_removing_a_directory_that_is_already_gone_is_not_an_error(
    tmp_path: pathlib.Path,
) -> None:
    remove_tree(tmp_path / "absent")


def test_the_ladder_ends_at_complete() -> None:
    steps = (
        Step("one", lambda: None, 1),
        Step("two", lambda: None, 3),
    )

    rungs = ladder(steps)

    assert rungs[-1][1] == COMPLETE_PERCENT


def test_the_ladder_is_weighted_rather_than_evenly_spaced() -> None:
    """Even spacing would send the bar to the end within a few hundredths."""
    steps = (
        Step("slow", lambda: None, EXTRACT_WEIGHT),
        Step("quick", lambda: None, 1),
    )

    first, _second = ladder(steps)

    assert first[1] > COMPLETE_PERCENT // 2


def test_an_empty_ladder_is_empty_rather_than_a_division_by_zero() -> None:
    assert ladder(()) == ()


def test_an_install_unpacks_before_it_records(tmp_path: pathlib.Path) -> None:
    plan = InstallPlan(target=tmp_path / "install", version="1.0.0")

    steps = install_steps(plan, tmp_path / "payload.zip", StepLog())

    assert steps[0].name.startswith("Unpacking")
    assert len(steps) == 4


def test_a_removal_takes_the_shortcuts_before_the_files(
    tmp_path: pathlib.Path,
) -> None:
    steps = uninstall_steps(tmp_path / "install", StepLog())

    assert steps[0].name.startswith("Removing the shortcuts")
    assert steps[-1].name.startswith("Removing the files")


def test_the_step_log_is_flushed_as_it_goes() -> None:
    log = StepLog()

    log.write("one")
    log.write("two")

    assert log.path.read_text(encoding="utf-8").splitlines() == ["one", "two"]
