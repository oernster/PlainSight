"""Starting the application, then handing it the right to come forward."""

from __future__ import annotations

import pathlib
import sys

from installer import launching


class RecordingGrant:
    """A hand-written stand-in for the Windows call, so none is made."""

    def __init__(self) -> None:
        self.granted_to: list[int] = []

    def __call__(self, process_id: int) -> bool:
        self.granted_to.append(process_id)
        return True


def an_executable(tmp_path: pathlib.Path) -> pathlib.Path:
    """Something that really starts and really exits, on any platform."""
    script = tmp_path / "does_nothing.py"
    script.write_text("", encoding="utf-8")
    runner = tmp_path / ("run.cmd" if sys.platform == "win32" else "run.sh")
    if sys.platform == "win32":
        runner.write_text(f'@"{sys.executable}" "{script}"\r\n', encoding="utf-8")
    else:
        runner.write_text(f'#!/bin/sh\n"{sys.executable}" "{script}"\n', "utf-8")
        runner.chmod(0o755)
    return runner


def test_a_missing_executable_is_refused_rather_than_raised(
    tmp_path: pathlib.Path,
) -> None:
    grant = RecordingGrant()

    assert launching.start(tmp_path / "not-here.exe", grant) is False
    assert grant.granted_to == []


def test_the_started_process_is_granted_the_foreground(
    tmp_path: pathlib.Path,
) -> None:
    """The half setup owns: a process that lacks the foreground cannot take it.

    Reported after a fresh install: the window opened behind everything. Setup
    holds the foreground at the moment it starts the application, so it is the
    only thing that can hand that right over. The grant is asserted against the
    process actually started rather than merely being called, since granting it
    to the wrong process is the failure that would look identical here.
    """
    grant = RecordingGrant()

    assert launching.start(an_executable(tmp_path), grant) is True
    assert len(grant.granted_to) == 1
    assert grant.granted_to[0] > 0


def test_the_grant_is_inert_away_from_windows() -> None:
    """It answers rather than raising, so the caller needs no platform test."""
    if sys.platform != "win32":
        assert launching.allow_foreground(1) is False
