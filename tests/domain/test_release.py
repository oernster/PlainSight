"""A release and the document it becomes: small header, notes unchanged."""

from __future__ import annotations

import pytest

from plainsight.domain.release import (
    NO_NOTES,
    InvalidRelease,
    Release,
    display_date,
    plain,
    release_markdown,
)

PAGE = "https://github.com/oernster/PlainSight/releases/tag/v1.4.0"
NOTES = (
    "## What's new\n\n"
    "- **Bold** item with `code`\n"
    "- A [link](https://example.com)\n\n"
    "```python\nprint('hello')\n```\n\n"
    "| a | b |\n|---|---|\n| 1 | 2 |\n"
)


def a_release(**changes: object) -> Release:
    fields: dict[str, object] = {
        "source_id": 7,
        "tag": "v1.4.0",
        "title": "PlainSight v1.4.0",
        "published_at": "2026-09-29T10:15:00Z",
        "prerelease": False,
        "body": NOTES,
        "source_url": PAGE,
    }
    fields.update(changes)
    return Release(**fields)  # type: ignore[arg-type]


def test_a_release_becomes_its_header_then_its_body_unchanged() -> None:
    text = release_markdown(a_release())

    assert text == (
        "# PlainSight v1.4.0\n\n"
        "**Tag:** v1.4.0  \n"
        "**Released:** 29 September 2026  \n"
        f"**Source:** [GitHub]({PAGE})\n\n"
        "---\n\n" + NOTES
    )


def test_a_prerelease_says_so_and_an_ordinary_release_does_not() -> None:
    assert "**Pre-release:** Yes" in release_markdown(a_release(prerelease=True))
    assert "Pre-release" not in release_markdown(a_release())


def test_a_release_with_no_body_still_has_a_document() -> None:
    for empty in ("", "   \n\n"):
        text = release_markdown(a_release(body=empty))

        assert text.endswith(f"---\n\n{NO_NOTES}\n")


def test_a_release_with_no_title_is_headed_by_its_tag() -> None:
    for blank in ("", "  \n "):
        assert release_markdown(a_release(title=blank)).startswith("# v1.4.0\n")


def test_an_undated_release_has_no_released_line() -> None:
    assert "Released" not in release_markdown(a_release(published_at=""))


def test_unicode_survives_in_the_title_and_the_notes() -> None:
    text = release_markdown(
        a_release(title="Größe → \U0001f680", body="Ünïcödé 日本語\n")
    )

    assert text.startswith("# Größe → \U0001f680\n")
    assert text.endswith("Ünïcödé 日本語\n")


def test_the_notes_keep_their_own_line_endings_and_gain_one_only_if_missing() -> None:
    assert release_markdown(a_release(body="a\r\nb")).endswith("a\r\nb\n")
    assert release_markdown(a_release(body="a\n")).endswith("---\n\na\n")


def test_a_title_cannot_become_markup_or_a_second_line() -> None:
    text = release_markdown(
        a_release(title="*Bold* <script>x</script> [link](y) #1\n# Injected")
    )
    heading = text.split("\n", 1)[0]

    assert heading == (
        r"# \*Bold\* &lt;script&gt;x&lt;/script&gt; \[link\](y) \#1 \# Injected"
    )


def test_a_source_that_is_not_a_github_page_is_named_rather_than_linked() -> None:
    for address in ("", "javascript:alert(1)", "https://evil.example/x", PAGE + ")"):
        text = release_markdown(a_release(source_url=address))

        assert "**Source:** GitHub\n" in text


def test_the_heading_collapses_whitespace() -> None:
    assert a_release(title="  a \t  b ").heading == "a b"


def test_display_date_reads_as_words() -> None:
    assert display_date("2026-01-05T00:00:00Z") == "5 January 2026"
    assert display_date("2025-12-31T23:59:59Z") == "31 December 2025"
    assert display_date("") == ""


def test_plain_text_escapes_only_what_markdown_would_read() -> None:
    assert plain("v1.4.0-beta+1 (final)!") == "v1.4.0-beta+1 (final)!"
    assert plain("a_b*c`d\\e") == r"a\_b\*c\`d\\e"


@pytest.mark.parametrize(
    "changes",
    [
        {"tag": ""},
        {"tag": "   "},
        {"published_at": "2026-09-29"},
        {"published_at": "2026-09-29T10:15:00.123Z"},
    ],
)
def test_a_release_that_cannot_be_named_or_placed_is_refused(
    changes: dict[str, object],
) -> None:
    with pytest.raises(InvalidRelease):
        a_release(**changes)
