"""The listing's idea of an empty page is the reading surface's own.

A page is empty when the pane would show no text for it. That is Qt's decision,
since Qt draws the page, so the listing's judgement is held to what a Qt text
document actually shows for the same markup rather than to a list written from
memory.
"""

from __future__ import annotations

import pytest
from PySide6.QtGui import QTextDocument
from PySide6.QtWidgets import QApplication

from plainsight.infrastructure.html_text import shows_text

SAMPLES = (
    "<script>var a = 1;</script>",
    "<style>p { color: red }</style>",
    "<html><head><title>A title</title></head><body></body></html>",
    "<head>stray</head><body></body>",
    "<!-- nothing to see -->",
    "<p>&nbsp;</p>",
    "<div id='ui'></div><script src='bundle.js'></script>",
    "<noscript>Enable scripts</noscript>",
    "<template>Inside a template</template>",
    "<p>Words</p>",
    "<script>ignored</script><p>After</p>",
    "<head><title>Head never closed</title><body>Body text</body>",
)


@pytest.mark.parametrize("markup", SAMPLES)
def test_the_listing_and_the_pane_agree_on_whether_a_page_shows_text(
    application: QApplication, markup: str
) -> None:
    document = QTextDocument()
    document.setHtml(markup)

    assert shows_text(markup) == bool(document.toPlainText().strip())
