"""The setup program's colours, held to the one rule a colour has to meet.

Text has to be readable on the fill behind it. That is arithmetic rather than
taste, so it is measured against the WCAG AA ratio rather than judged by eye:
the primary button used to draw the accent on the selection fill at 3.34 to 1,
which looked deliberate and was not readable.
"""

from __future__ import annotations

import pytest

from installer import theme
from tests.contrast import AA_RATIO, contrast

BOTH = (theme.DARK, theme.LIGHT)


def test_the_measure_agrees_with_the_two_ends_it_is_defined_by() -> None:
    """Black on white is 21 to 1 and a colour on itself is 1 to 1."""
    assert round(contrast("#000000", "#ffffff")) == 21
    assert contrast("#7c6cf0", "#7c6cf0") == pytest.approx(1.0)


@pytest.mark.parametrize("palette", BOTH, ids=("dark", "light"))
def test_the_primary_button_text_is_readable_on_its_own_fill(palette) -> None:
    assert contrast(palette.selection_text, palette.selection) >= AA_RATIO


@pytest.mark.parametrize("palette", BOTH, ids=("dark", "light"))
def test_the_body_text_is_readable_on_the_surfaces_it_sits_on(palette) -> None:
    for behind in (palette.window, palette.surface, palette.alt):
        assert contrast(palette.text, behind) >= AA_RATIO


@pytest.mark.parametrize("palette", BOTH, ids=("dark", "light"))
def test_the_danger_button_text_is_readable_on_its_own_fill(palette) -> None:
    assert contrast(palette.danger, palette.danger_soft) >= AA_RATIO


@pytest.mark.parametrize("palette", BOTH, ids=("dark", "light"))
def test_the_primary_button_no_longer_draws_the_accent(palette) -> None:
    """The accent is a fill and a marker here, never the text on the selection."""
    assert palette.selection_text != palette.accent


@pytest.mark.parametrize("palette", BOTH, ids=("dark", "light"))
def test_the_stylesheet_dresses_the_primary_button_in_that_token(palette) -> None:
    style = theme.stylesheet(palette)

    assert f"background: {palette.selection}" in style
    assert f"color: {palette.selection_text}" in style
