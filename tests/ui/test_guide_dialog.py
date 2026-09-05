"""The guide: what it names, with the real picture rather than a description.

A guide showing something other than the icon the tray draws is worse than no
guide, so what is asserted here is that every picture in it is resolved
through the same asset lookup the tray uses, against the same file names the
tray declares.
"""

from __future__ import annotations

import re

import pytest
from PySide6.QtWidgets import QApplication

from plainsight.infrastructure.resources import BundledAssets
from plainsight.ui.bottom_tray import DONATE_ICON, MODEL_LICENCE_ICON, UI_LICENCE_ICON
from plainsight.ui.guide_dialog import GuideDialog, guide_html
from plainsight.ui.theme import DARK
from plainsight.ui.top_tray import (
    CHOOSE_EDITOR_ICON,
    DARK_MODE_ICON,
    FOLDER_ICON,
    HELP_ICON,
    LAUNCH_EDITOR_ICON,
    LIGHT_MODE_ICON,
    OPEN_FILE_ICON,
)

NAMED_IN_THE_TRAYS = (
    FOLDER_ICON,
    OPEN_FILE_ICON,
    CHOOSE_EDITOR_ICON,
    LAUNCH_EDITOR_ICON,
    LIGHT_MODE_ICON,
    DARK_MODE_ICON,
    HELP_ICON,
    DONATE_ICON,
    UI_LICENCE_ICON,
    MODEL_LICENCE_ICON,
)


class NoAssets:
    """An asset lookup that finds nothing, as an unbundled build would."""

    def find(self, name: str) -> str | None:
        return None


@pytest.fixture
def html() -> str:
    return guide_html(BundledAssets())


def test_every_control_in_the_trays_is_shown_as_its_own_picture(html: str) -> None:
    """Never a description in words and never a stand-in emoji."""
    sources = re.findall(r'<img src="([^"]+)"', html)

    assert len(sources) >= len(NAMED_IN_THE_TRAYS)
    for icon in NAMED_IN_THE_TRAYS:
        stem = icon.rsplit(".", 1)[0]
        assert any(stem in source for source in sources), icon


def test_the_pictures_are_addressed_as_files_the_pane_can_reach(html: str) -> None:
    """A path with a space in it has to survive being put in an attribute."""
    for source in re.findall(r'<img src="([^"]+)"', html):
        assert source.startswith("file:///")
        assert " " not in source


def test_a_missing_picture_costs_its_picture_and_not_the_guide() -> None:
    """The line still reads; a build that bundled nothing still opens this."""
    bare = guide_html(NoAssets())

    assert "<img" not in bare
    assert "choose the folder your documents live in" in bare


def test_it_says_what_each_kind_of_document_becomes(html: str) -> None:
    """The one thing no screen can state while it is happening."""
    for kind in ("Markdown", "Plain text", "HTML", "Word", "PDF"):
        assert f"<b>{kind}</b>" in html


def test_the_guide_opens_on_the_reading_pane_and_can_be_closed(
    application: QApplication,
) -> None:
    dialog = GuideDialog(DARK, BundledAssets())
    dialog.show()

    assert dialog.body.toPlainText().strip()
    assert "How" in dialog.windowTitle()

    dialog.accept()
    assert not dialog.isVisible()
