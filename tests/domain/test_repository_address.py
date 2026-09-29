"""Which repository an address names; then every address that names none."""

from __future__ import annotations

import pytest

from plainsight.domain import repository_address as parsing
from plainsight.domain.repository_address import (
    InvalidRepositoryAddress,
    RepositoryAddress,
    parse_repository_address,
)

PLAINSIGHT = RepositoryAddress(owner="oernster", name="PlainSight")


@pytest.mark.parametrize(
    "text",
    [
        "oernster/PlainSight",
        "github.com/oernster/PlainSight",
        "https://github.com/oernster/PlainSight",
        "https://github.com/oernster/PlainSight/",
        "  https://github.com/oernster/PlainSight/  \n",
        "http://github.com/oernster/PlainSight",
        "https://www.github.com/oernster/PlainSight",
        "HTTPS://GitHub.com/oernster/PlainSight",
        "www.github.com/oernster/PlainSight/",
        "https://github.com/oernster/PlainSight?tab=readme-ov-file",
        "https://github.com/oernster/PlainSight#readme",
        "https://github.com/oernster/PlainSight.git",
        "oernster/PlainSight/",
    ],
)
def test_every_accepted_form_names_the_same_repository(text: str) -> None:
    assert parse_repository_address(text) == PLAINSIGHT


@pytest.mark.parametrize(
    "text",
    [
        "https://github.com/oernster/PlainSight/releases",
        "https://github.com/oernster/PlainSight/releases/",
        "https://github.com/oernster/PlainSight/releases/tag/v2.3.3",
        "https://github.com/oernster/PlainSight/tree/main/docs",
        "github.com/oernster/PlainSight/issues/12",
    ],
)
def test_a_recognised_sub_page_names_its_repository(text: str) -> None:
    assert parse_repository_address(text) == PLAINSIGHT


@pytest.mark.parametrize(
    ("text", "reason"),
    [
        ("", parsing.EMPTY),
        ("   ", parsing.EMPTY),
        ("https://github.com/", parsing.NO_OWNER),
        ("https://github.com", parsing.NO_OWNER),
        ("github.com", parsing.NO_OWNER),
        ("PlainSight", parsing.NO_OWNER),
        ("https://github.com/oernster", parsing.NO_REPOSITORY),
        ("https://github.com/oernster/", parsing.NO_REPOSITORY),
        ("https://gitlab.com/oernster/PlainSight", parsing.OTHER_HOST),
        ("https://github.com.evil.example/oernster/PlainSight", parsing.OTHER_HOST),
        ("ftp://github.com/oernster/PlainSight", parsing.OTHER_SCHEME),
        ("https://github.com/oernster/PlainSight/nonsense", parsing.NOT_A_REPOSITORY),
        ("https://github.com/oernster//PlainSight", parsing.NOT_A_REPOSITORY),
        ("https://github.com/orgs/acme", parsing.NOT_A_REPOSITORY),
        ("https://github.com/settings/profile", parsing.NOT_A_REPOSITORY),
        ("a/b/c", parsing.NOT_A_REPOSITORY),
        ("gitlab.com/oernster/PlainSight", parsing.NOT_A_REPOSITORY),
        ("https://github.com/-bad/PlainSight", parsing.BAD_OWNER),
        ("https://github.com/o_e/PlainSight", parsing.BAD_OWNER),
        ("https://github.com/oernster/..", parsing.BAD_REPOSITORY),
        ("https://github.com/oernster/.", parsing.BAD_REPOSITORY),
        ("https://github.com/oernster/Plain Sight", parsing.BAD_REPOSITORY),
        ("oernster/" + "x" * 101, parsing.BAD_REPOSITORY),
    ],
)
def test_each_malformed_address_is_refused_with_a_reason(
    text: str, reason: str
) -> None:
    with pytest.raises(InvalidRepositoryAddress) as refused:
        parse_repository_address(text)

    assert str(refused.value) == reason


def test_a_repository_called_git_suffix_alone_is_not_stripped_to_nothing() -> None:
    """``.git`` is a legal repository name; only a suffix on a longer one goes."""
    assert parse_repository_address("acme/.git").name == ".git"


def test_the_web_address_is_the_repository_page() -> None:
    assert PLAINSIGHT.web_url == "https://github.com/oernster/PlainSight"


def test_two_spellings_differing_in_case_are_one_repository() -> None:
    other = RepositoryAddress(owner="OERNSTER", name="plainsight")

    assert PLAINSIGHT.same_repository(other)
    assert not PLAINSIGHT.same_repository(RepositoryAddress("oernster", "Other"))
