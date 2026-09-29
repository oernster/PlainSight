"""What the import says: a sentence for every problem, never a status code."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from plainsight.application.release_import import (
    CollectionWriteFailed,
    GitHubUnavailable,
    ImportOutcome,
    ImportProblem,
    ImportStage,
    MalformedResponse,
    NetworkUnavailable,
    NoPublishedReleases,
    RateLimited,
    RepositoryInaccessible,
    RepositoryNotFound,
    TimedOut,
)
from plainsight.domain.release_collection import (
    CollectionEntry,
    RefreshPlan,
    ReleaseCollection,
)
from plainsight.domain.repository_address import RepositoryAddress
from plainsight.ui import release_import_wording as wording

ADDRESS = RepositoryAddress("oernster", "PlainSight")
EVERY_PROBLEM = (
    RepositoryNotFound,
    RepositoryInaccessible,
    GitHubUnavailable,
    NetworkUnavailable,
    TimedOut,
    MalformedResponse,
    NoPublishedReleases,
    CollectionWriteFailed,
    RateLimited,
)


def an_outcome(refreshed: bool, **plan: tuple[str, ...]) -> ImportOutcome:
    entries = [CollectionEntry(n, f"v{n}", "", f"undated_v{n}.md", "") for n in (1, 2)]
    collection = ReleaseCollection.of(ADDRESS, entries)
    return ImportOutcome(
        root="/r",
        newest="/r/undated_v2.md",
        plan=RefreshPlan(collection=collection, **plan),
        refreshed=refreshed,
    )


@pytest.mark.parametrize("kind", EVERY_PROBLEM)
def test_every_problem_has_words_of_its_own(kind: type[ImportProblem]) -> None:
    message = wording.problem_message(kind())

    assert message and "HTTP" not in message
    assert not message.startswith("The import stopped unexpectedly")


def test_no_two_problems_share_their_words() -> None:
    messages = [wording.MESSAGES[kind] for kind in EVERY_PROBLEM]

    assert len(set(messages)) == len(messages)


def test_a_rate_limit_says_when_it_resets_in_local_time() -> None:
    epoch = 1_790_000_000
    expected = datetime.fromtimestamp(epoch, tz=UTC).astimezone().strftime("%H:%M")

    assert wording.problem_message(RateLimited(epoch)).endswith(
        f"It resets at {expected}."
    )
    assert wording.problem_message(RateLimited()).endswith("within the hour.")


def test_an_unforeseen_failure_is_still_said() -> None:
    assert wording.problem_message(KeyError("x")) == (
        "The import stopped unexpectedly: 'x'"
    )


def test_each_stage_is_said() -> None:
    assert wording.stage_message(ImportStage.RETRIEVING, 0) == wording.RETRIEVING
    assert wording.stage_message(ImportStage.RETRIEVING, 300).endswith("300 so far")
    assert wording.stage_message(ImportStage.WRITING, 4) == wording.WRITING


def test_the_summary_tells_a_first_import_from_a_refresh() -> None:
    assert wording.outcome_summary(an_outcome(False), "o/r") == (
        "Imported 2 releases of o/r"
    )
    refreshed = an_outcome(True, added=("a.md",), updated=("b.md", "c.md"))
    assert wording.outcome_summary(refreshed, "o/r") == (
        "Refreshed o/r: 1 new, 2 updated"
    )


def test_nothing_kept_means_nothing_to_say() -> None:
    assert wording.kept_notice(an_outcome(True)) == ""


def test_what_was_kept_is_listed_by_file() -> None:
    notice = wording.kept_notice(
        an_outcome(True, kept_edited=("a.md",), kept_withdrawn=("b.md",))
    )

    assert notice == (
        f"{wording.KEPT_EDITED}\n• a.md\n\n{wording.KEPT_WITHDRAWN}\n• b.md"
    )
