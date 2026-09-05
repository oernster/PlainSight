"""The application's colours, held to the same rule the setup program is.

Three pairings were under the readable ratio and each looked deliberate: the
selected row, every heading in a rendered skill and a link in the light theme.
Judging colour by eye is what let them stand, so they are measured here.
"""

from __future__ import annotations

import pytest

from plainsight.ui import theme
from tests.contrast import AA_RATIO, contrast

BOTH = (theme.DARK, theme.LIGHT)


@pytest.mark.parametrize("palette", BOTH, ids=("dark", "light"))
def test_the_selected_row_text_is_readable_on_its_own_fill(palette) -> None:
    assert contrast(palette.selection_text, palette.selection) >= AA_RATIO


@pytest.mark.parametrize("palette", BOTH, ids=("dark", "light"))
def test_a_heading_is_readable_on_the_page_it_is_drawn_on(palette) -> None:
    assert contrast(palette.accent, palette.panel) >= AA_RATIO


@pytest.mark.parametrize("palette", BOTH, ids=("dark", "light"))
def test_a_link_is_readable_on_the_page_it_is_drawn_on(palette) -> None:
    assert contrast(palette.ring, palette.panel) >= AA_RATIO


@pytest.mark.parametrize("palette", BOTH, ids=("dark", "light"))
def test_the_body_and_the_quieter_text_are_both_readable(palette) -> None:
    for front in (palette.text, palette.muted):
        assert contrast(front, palette.panel) >= AA_RATIO
        assert contrast(front, palette.window) >= AA_RATIO


def test_the_dark_theme_keeps_its_selection_apart_from_its_accent() -> None:
    """One token cannot be both light enough to read and dark enough to sit on.

    A heading wants the lighter violet and white on the selected row wants the
    darker one, so the dark theme names the two separately.
    """
    assert theme.DARK.selection != theme.DARK.accent


def test_the_stylesheet_dresses_the_selected_row_in_the_selection_fill() -> None:
    style = theme.stylesheet(theme.DARK)

    assert f"background: {theme.DARK.selection}" in style
