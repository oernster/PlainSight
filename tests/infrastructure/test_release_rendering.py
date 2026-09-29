"""A generated release document through the real renderer, as the pane gets it."""

from __future__ import annotations

from plainsight.domain.document import DocumentKind
from plainsight.domain.release import Release, release_markdown
from plainsight.infrastructure.renderer import DocumentHtmlRenderer

PAGE = "https://github.com/oernster/PlainSight/releases/tag/v1.4.0"


def rendered(**changes: object) -> str:
    fields: dict[str, object] = {
        "source_id": 1,
        "tag": "v1.4.0",
        "title": "PlainSight v1.4.0",
        "published_at": "2026-09-29T10:15:00Z",
        "prerelease": True,
        "body": "## Changes\n\n| a | b |\n|---|---|\n| 1 | 2 |\n",
        "source_url": PAGE,
    }
    fields.update(changes)
    text = release_markdown(Release(**fields))  # type: ignore[arg-type]
    return DocumentHtmlRenderer().render(text, DocumentKind.MARKDOWN)


def test_each_header_line_stands_on_a_line_of_its_own() -> None:
    html = rendered()

    assert "<strong>Tag:</strong> v1.4.0<br />" in html
    assert "<strong>Released:</strong> 29 September 2026<br />" in html
    assert "<strong>Pre-release:</strong> Yes<br />" in html
    assert f'<strong>Source:</strong> <a href="{PAGE}">GitHub</a>' in html


def test_the_notes_are_rendered_as_the_markdown_they_are() -> None:
    html = rendered()

    assert "<h2>Changes</h2>" in html
    assert "<table>" in html
    assert "<hr />" in html


def test_a_hostile_title_shows_as_the_text_it_was() -> None:
    html = rendered(title="*x* <b>y</b> [z](q) #1")

    assert "<h1>*x* &lt;b&gt;y&lt;/b&gt; [z](q) #1</h1>" in html


def test_a_plain_tag_reads_without_any_backslash() -> None:
    html = rendered(tag="v1.4.0-beta+1")

    assert "\\" not in html
    assert "v1.4.0-beta+1" in html
