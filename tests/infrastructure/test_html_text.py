"""Whether a page shows any text once its scripts, styles and markup are gone.

Each case was measured against the reading surface first: a Qt text document
given the same markup shows nothing for a script, a style, a title, a head, a
comment or a lone non-breaking space; it shows what a ``noscript`` or a
``template`` holds. ``tests/ui/test_html_text_agrees_with_the_pane.py`` keeps
the two in step.
"""

from __future__ import annotations

import pytest

from plainsight.infrastructure.html_text import shows_text

# The shapes of the two Flask templates that prompted this: a script tag and
# an empty element, with a title in the head.
SWAGGER_SHAPE = (
    "<!doctype html>\n<html lang='en'>\n<head>\n  <meta charset='utf-8'>\n"
    "  <title>Client API: Swagger UI</title>\n"
    "  <link rel='stylesheet' href=\"{{ url_for('static') }}\">\n</head>\n"
    "<body>\n  <div id='swagger-ui'></div>\n"
    "  <script src=\"{{ url_for('bundle') }}\"></script>\n"
    "  <script>\n    window.ui = SwaggerUIBundle({dom_id: '#swagger-ui'});\n"
    "  </script>\n</body>\n</html>\n"
)
REDOC_SHAPE = (
    "<!doctype html>\n<html>\n<head><title>Client API: ReDoc</title></head>\n"
    "<body>\n  <redoc spec-url=\"{{ url_for('openapi') }}\"></redoc>\n"
    "  <script src=\"{{ url_for('redoc') }}\"></script>\n</body>\n</html>\n"
)


@pytest.mark.parametrize(
    "markup",
    [
        "",
        "   \n",
        "<script>var shown = 'never';</script>",
        "<SCRIPT>var shown = 'never';</SCRIPT>",
        "<style>p { color: red }</style>",
        "<html><head><title>Only a title</title></head><body></body></html>",
        "<head>stray words in the head</head><body></body>",
        "<!-- a comment says nothing to a reader -->",
        "<p>&nbsp;</p>",
        SWAGGER_SHAPE,
        REDOC_SHAPE,
    ],
)
def test_a_page_of_markup_alone_shows_no_text(markup: str) -> None:
    assert not shows_text(markup)


@pytest.mark.parametrize(
    "markup",
    [
        "<p>Words</p>",
        "Words with no markup at all",
        "<noscript>Enable scripts</noscript>",
        "<template>Inside a template</template>",
        "<script>ignored</script><p>After the script</p>",
        "<head><title>Title</title></head><body>Body text</body>",
        "<head><title>Head never closed</title><body>Body text</body>",
    ],
)
def test_a_page_with_words_on_it_shows_text(markup: str) -> None:
    assert shows_text(markup)
