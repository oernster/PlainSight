"""Everything the release import says, in one place.

Each problem is told as what happened, then what to do next where there is
something to do. A reader told "HTTP 403" has been told nothing; a reader told when
GitHub's allowance returns can simply come back then.
"""

from __future__ import annotations

from datetime import UTC, datetime

from ..application.release_import import (
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

TITLE = "Import GitHub Releases"
FIELD_LABEL = "Repository address"
DEFAULT_ADDRESS = "https://github.com/"
EXAMPLE_ADDRESS = "https://github.com/oernster/PlainSight"
EXAMPLE = f"For example: {EXAMPLE_ADDRESS}"
IMPORT_LABEL = "Import"
CANCEL_LABEL = "Cancel"

RETRIEVING = "Retrieving releases…"
RETRIEVED_SO_FAR = "Retrieving releases… {count} so far"
WRITING = "Creating release notes…"
STOPPING = "Stopping after the current request…"
FINISHING = "Finishing the files already being written…"

RESET_AT = "It resets at {time}."
RESET_UNKNOWN = "It resets within the hour."
RESET_FORMAT = "%H:%M"
UNEXPECTED = "The import stopped unexpectedly: {detail}"

MESSAGES: dict[type[ImportProblem], str] = {
    RepositoryNotFound: (
        "GitHub has no public repository at that address. A private "
        "repository is reported the same way."
    ),
    RepositoryInaccessible: "GitHub refused access to this repository's releases.",
    GitHubUnavailable: "GitHub is not answering properly just now. Try again later.",
    NetworkUnavailable: "GitHub could not be reached. Check the connection.",
    TimedOut: "GitHub took too long to answer. Try again.",
    MalformedResponse: (
        "GitHub's answer did not describe releases, so nothing was imported."
    ),
    NoPublishedReleases: "No published releases were found for this repository.",
    CollectionWriteFailed: (
        "The release notes could not be written. Anything imported before is "
        "unchanged."
    ),
    RateLimited: (
        "GitHub's limit on requests made without an account has been reached."
    ),
}

IMPORTED = "Imported {count} releases of {name}"
REFRESHED = "Refreshed {name}: {added} new, {updated} updated"
KEPT_EDITED = (
    "These release notes changed on GitHub after you edited them here. Your "
    "versions were kept:"
)
KEPT_WITHDRAWN = "These releases are no longer on GitHub. Their notes were kept here:"
LIST_ITEM = "\n• {name}"


def stage_message(stage: ImportStage, count: int) -> str:
    """What the dialog says the import is doing now."""
    if stage is ImportStage.WRITING:
        return WRITING
    return RETRIEVED_SO_FAR.format(count=count) if count else RETRIEVING


def problem_message(problem: Exception) -> str:
    """What to tell the reader about a problem, in a sentence or two."""
    message = MESSAGES.get(type(problem))
    if message is None:
        return UNEXPECTED.format(detail=problem)
    if isinstance(problem, RateLimited):
        return f"{message} {_reset(problem.reset_epoch)}"
    return message


def outcome_summary(outcome: ImportOutcome, name: str) -> str:
    """One line for the status bar saying what the import did."""
    plan = outcome.plan
    if not outcome.refreshed:
        return IMPORTED.format(count=len(plan.collection.entries), name=name)
    return REFRESHED.format(name=name, added=len(plan.added), updated=len(plan.updated))


def kept_notice(outcome: ImportOutcome) -> str:
    """What was kept rather than overwritten; empty when nothing was."""
    parts = []
    for heading, names in (
        (KEPT_EDITED, outcome.plan.kept_edited),
        (KEPT_WITHDRAWN, outcome.plan.kept_withdrawn),
    ):
        if names:
            listed = "".join(LIST_ITEM.format(name=one) for one in names)
            parts.append(f"{heading}{listed}")
    return "\n\n".join(parts)


def _reset(epoch: int | None) -> str:
    """When the allowance returns, in the reader's own time of day."""
    if epoch is None:
        return RESET_UNKNOWN
    local = datetime.fromtimestamp(epoch, tz=UTC).astimezone()
    return RESET_AT.format(time=local.strftime(RESET_FORMAT))
