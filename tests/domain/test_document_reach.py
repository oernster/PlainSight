"""What a document may reach: the links it hands on and the files it may show.

Pure string rules, so every address here is only ever parsed, never opened.
"""

from __future__ import annotations

import pytest

from plainsight.domain.document_reach import (
    LinkAction,
    is_inline,
    link_action,
    resource_path,
)

WINDOWS_DOCUMENT = "C:\\Users\\reader\\notes\\page.md"
POSIX_DOCUMENT = "/home/reader/notes/page.md"
SHARE_DOCUMENT = "\\\\server\\share\\notes\\page.md"


@pytest.mark.parametrize(
    "address",
    (
        "https://example.invalid/page",
        "HTTPS://example.invalid/page",
        "http://example.invalid/page",
        "mailto:someone@example.invalid",
        "  https://example.invalid/padded  ",
    ),
)
def test_a_web_page_or_a_mail_is_followed(address: str) -> None:
    assert link_action(address) is LinkAction.FOLLOW


@pytest.mark.parametrize(
    "address",
    (
        "search-ms:query=x&crumb=location:\\\\server\\share",
        "ms-msdt:/id PCWDiagnostic",
        "ms-settings:privacy",
        "smb://server/share",
        "javascript:alert(1)",
        "file:///C:/Users/reader/other.html",
        "file://server/share/other.html",
        "ftp://example.invalid/file",
        "http:no-host",
        "https:///no-host",
        "other.md",
        "../other.md",
        "",
        "C:/Users/reader/other.html",
    ),
)
def test_every_other_link_is_ignored(address: str) -> None:
    assert link_action(address) is LinkAction.IGNORE


def test_a_link_to_a_place_in_the_page_stays_in_the_page() -> None:
    assert link_action("#a-heading") is LinkAction.IN_PAGE


@pytest.mark.parametrize(
    "source",
    (
        "file://server/share/pic.png",
        "file://127.0.0.1/c$/pic.png",
        "//server/share/pic.png",
        "\\\\server\\share\\pic.png",
        "\\/server/share/pic.png",
        "%5C%5Cserver%5Cshare%5Cpic.png",
        "file:%2F%2Fserver/share/pic.png",
        "file:////server/share/pic.png",
        "http://example.invalid/pic.png",
        "https://example.invalid/pic.png",
        "smb://server/share/pic.png",
        "ftp://example.invalid/pic.png",
        "qrc:/pic.png",
        "data:image/png;base64,AAAA",
        "C:pic.png",
        "",
        "   ",
    ),
)
def test_a_source_naming_a_host_or_another_scheme_is_refused(source: str) -> None:
    assert resource_path(source, WINDOWS_DOCUMENT) is None
    assert resource_path(source, POSIX_DOCUMENT) is None


@pytest.mark.parametrize(
    ("source", "expected"),
    (
        ("C:/pictures/pic.png", "C:/pictures/pic.png"),
        ("C:\\pictures\\pic.png", "C:/pictures/pic.png"),
        ("c:%5Cpictures%5Cpic.png", "c:/pictures/pic.png"),
        ("file:///C:/pictures/my%20pic.png", "C:/pictures/my pic.png"),
        ("file://localhost/C:/pictures/pic.png", "C:/pictures/pic.png"),
        ("FILE:///C:/pictures/pic.png", "C:/pictures/pic.png"),
        ("/home/reader/pic.png", "/home/reader/pic.png"),
        ("file:///home/reader/pic.png", "/home/reader/pic.png"),
        ("C:/pictures/../other/./pic.png", "C:/other/pic.png"),
        ("C:/../../pic.png", "C:/pic.png"),
    ),
)
def test_a_local_absolute_source_is_read_where_it_names(
    source: str, expected: str
) -> None:
    assert resource_path(source, WINDOWS_DOCUMENT) == expected


@pytest.mark.parametrize(
    ("source", "expected"),
    (
        ("pic.png", "C:/Users/reader/notes/pic.png"),
        ("./images/pic.png", "C:/Users/reader/notes/images/pic.png"),
        ("images\\pic.png", "C:/Users/reader/notes/images/pic.png"),
        ("my%20pic.png", "C:/Users/reader/notes/my pic.png"),
        ("../pictures/pic.png", "C:/Users/reader/pictures/pic.png"),
        ("../notes/pic.png", "C:/Users/reader/notes/pic.png"),
        ("../../../../../pic.png", "C:/pic.png"),
    ),
)
def test_a_relative_source_is_read_from_the_documents_own_folder(
    source: str, expected: str
) -> None:
    assert resource_path(source, WINDOWS_DOCUMENT) == expected


def test_a_relative_source_on_posix_reads_from_the_documents_folder() -> None:
    assert resource_path("pic.png", POSIX_DOCUMENT) == "/home/reader/notes/pic.png"
    assert resource_path("../../../../x.png", POSIX_DOCUMENT) == "/x.png"


def test_a_document_at_a_root_never_makes_a_network_path() -> None:
    assert resource_path("pic.png", "/page.md") == "/pic.png"
    assert resource_path("pic.png", "C:\\page.md") == "C:/pic.png"


def test_a_document_on_a_share_shows_the_pictures_in_its_own_folder() -> None:
    """The reader chose that share; the folder they opened is theirs to read."""
    assert resource_path("pic.png", SHARE_DOCUMENT) == "//server/share/notes/pic.png"
    assert (
        resource_path("sub/../pic.png", SHARE_DOCUMENT)
        == "//server/share/notes/pic.png"
    )


@pytest.mark.parametrize(
    "source",
    ("../pic.png", "../../pic.png", "../../../../other/share/pic.png"),
)
def test_a_relative_source_leaving_a_shared_folder_is_refused(source: str) -> None:
    """Out of the reader's chosen folder and still on the network: refused."""
    assert resource_path(source, SHARE_DOCUMENT) is None


def test_a_relative_source_with_no_document_is_refused() -> None:
    assert resource_path("pic.png", None) is None


def test_a_relative_source_beside_a_relative_document_is_refused() -> None:
    """No folder it could honestly mean, so not the root of the disk either."""
    assert resource_path("pic.png", "page.md") is None
    assert resource_path("pic.png", "notes/page.md") is None


def test_an_absolute_local_source_needs_no_document() -> None:
    assert resource_path("C:/pictures/pic.png", None) == "C:/pictures/pic.png"


def test_only_a_data_address_is_inline() -> None:
    assert is_inline("data:image/png;base64,AAAA")
    assert is_inline("DATA:image/png;base64,AAAA")
    assert not is_inline("pic.png")
    assert not is_inline("https://example.invalid/data:")
