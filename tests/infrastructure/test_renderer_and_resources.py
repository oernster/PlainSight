"""Rendering a body; finding what the build bundled."""

from __future__ import annotations

from pathlib import Path

from skillsviewer.infrastructure.markdown_renderer import PythonMarkdownRenderer
from skillsviewer.infrastructure.platform import (
    FileSystemPathProbe,
    HomePlatformPaths,
    settings_path,
)
from skillsviewer.infrastructure.resources import (
    BundledAssets,
    find_asset,
    read_version,
)


def test_headings_and_code_fences_both_render() -> None:
    html = PythonMarkdownRenderer().render("# Title\n\n```py\nx = 1\n```\n")

    assert "<h1>Title</h1>" in html
    assert "<code" in html


def test_a_table_renders_as_a_table() -> None:
    html = PythonMarkdownRenderer().render("| a | b |\n|---|---|\n| 1 | 2 |\n")

    assert "<table>" in html


def test_the_version_comes_from_the_file_that_holds_it() -> None:
    expected = (
        (Path(__file__).resolve().parents[2] / "VERSION")
        .read_text(encoding="utf-8")
        .strip()
    )

    assert read_version() == expected


def test_the_bundled_artwork_is_found() -> None:
    """Every picture the user interface asks for is really in the build."""
    from skillsviewer.ui.about_dialog import APPLICATION_ICON
    from skillsviewer.ui.bottom_tray import (
        DONATE_ICON,
        MODEL_LICENCE_ICON,
        UI_LICENCE_ICON,
    )
    from skillsviewer.ui.top_tray import (
        CHOOSE_EDITOR_ICON,
        FOLDER_ICON,
        HELP_ICON,
        LAUNCH_EDITOR_ICON,
    )

    assets = BundledAssets()
    wanted = (
        APPLICATION_ICON,
        DONATE_ICON,
        UI_LICENCE_ICON,
        MODEL_LICENCE_ICON,
        FOLDER_ICON,
        CHOOSE_EDITOR_ICON,
        LAUNCH_EDITOR_ICON,
        HELP_ICON,
    )

    assert [name for name in wanted if assets.find(name) is None] == []


def test_an_asset_that_is_not_bundled_is_reported_as_absent() -> None:
    assert find_asset("no-such-asset.png") is None


def test_the_home_directory_is_reported() -> None:
    assert HomePlatformPaths().home_directory() == str(Path.home())


def test_the_probe_answers_for_a_path_that_is_there(tmp_path: Path) -> None:
    present = tmp_path / "here.txt"
    present.write_text("x", encoding="utf-8")

    assert FileSystemPathProbe().exists(str(present))
    assert not FileSystemPathProbe().exists(str(tmp_path / "absent.txt"))


def test_the_settings_file_sits_beneath_the_home_directory() -> None:
    assert settings_path().is_relative_to(Path.home())
