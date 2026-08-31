"""The module size cap and the danger band beneath it.

The band is derived from the cap rather than written as a second number, so the
two cannot drift apart.
"""

from __future__ import annotations

from pathlib import Path

from .layers import (
    BUILD_SCRIPTS,
    INSTALLER_ROOT,
    PACKAGE_ROOT,
    REPOSITORY_ROOT,
    is_build_output,
)

LINE_CAP = 400
BAND_FRACTION_PERCENT = 5
BAND_FLOOR = LINE_CAP - (LINE_CAP * BAND_FRACTION_PERCENT // 100)
TESTS_ROOT = REPOSITORY_ROOT / "tests"


def measured_files() -> tuple[Path, ...]:
    """Every file the cap applies to.

    The application package, the setup program's own interface and the tests.
    The build and packaging scripts are exempt; see BUILD_SCRIPTS.
    """
    found = [
        *PACKAGE_ROOT.rglob("*.py"),
        *INSTALLER_ROOT.rglob("*.py"),
        *TESTS_ROOT.rglob("*.py"),
    ]
    return tuple(
        p for p in found if p.name not in BUILD_SCRIPTS and not is_build_output(p)
    )


def line_count(path: Path) -> int:
    """Every line in the file, blank ones included."""
    return len(path.read_text(encoding="utf-8").splitlines())


def test_no_module_is_over_the_cap() -> None:
    over = [
        f"{path.name}: {line_count(path)}"
        for path in measured_files()
        if line_count(path) > LINE_CAP
    ]

    assert over == []


def test_no_module_sits_in_the_danger_band() -> None:
    banded = [
        f"{path.name}: {line_count(path)}"
        for path in measured_files()
        if BAND_FLOOR < line_count(path) <= LINE_CAP
    ]

    assert banded == []


def test_the_band_is_derived_from_the_cap() -> None:
    assert BAND_FLOOR == 380
