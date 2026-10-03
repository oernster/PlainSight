"""Importing a repository's release notes as a folder of documents.

GitHub is where the notes come from and nothing more: once imported they are
ordinary Markdown files in an ordinary folder, read exactly as any other.

The order is fixed and every network request happens before any write. So a
failure while asking GitHub, which is where almost every failure is, leaves the
disk exactly as it was; a stop asked for at any point before writing costs
nothing either.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum

from ..domain.release_collection import RefreshPlan, file_names_for, plan_refresh
from ..domain.repository_address import RepositoryAddress
from .ports import ReleaseCollectionStore, ReleaseHistorySource


class ImportProblem(Exception):
    """Why an import did not finish. Each kind is told apart by its class."""


class RepositoryNotFound(ImportProblem):
    """GitHub knows no such repository; else it will not say it exists."""


class RepositoryInaccessible(ImportProblem):
    """GitHub refused to show this repository's releases."""


class RateLimited(ImportProblem):
    """GitHub's allowance of requests is spent until ``reset_epoch``."""

    def __init__(self, reset_epoch: int | None = None) -> None:
        super().__init__(reset_epoch)
        self.reset_epoch = reset_epoch


class GitHubUnavailable(ImportProblem):
    """GitHub answered with a failure of its own."""


class NetworkUnavailable(ImportProblem):
    """GitHub could not be reached at all."""


class TimedOut(ImportProblem):
    """GitHub took too long to answer."""


class MalformedResponse(ImportProblem):
    """GitHub answered with something that does not describe releases."""


class NoPublishedReleases(ImportProblem):
    """The repository exists and has published no release."""


class CollectionWriteFailed(ImportProblem):
    """The folder could not be written; what was there before still is."""


class ImportCancelled(ImportProblem):
    """The reader stopped the import before anything was written."""


class ImportStage(Enum):
    """What an import is doing, for whoever is showing it."""

    RETRIEVING = "retrieving"
    WRITING = "writing"


@dataclass(frozen=True, slots=True)
class ImportOutcome:
    """A finished import: where the folder is and what changed in it."""

    root: str
    newest: str
    plan: RefreshPlan
    refreshed: bool


Report = Callable[[ImportStage, int], None]
Cancelled = Callable[[], bool]


@dataclass(frozen=True, slots=True)
class ReleaseImportService:
    """Reads every published release, then writes the folder they become."""

    source: ReleaseHistorySource
    store: ReleaseCollectionStore

    def import_releases(
        self, address: RepositoryAddress, report: Report, cancelled: Cancelled
    ) -> ImportOutcome:
        """Import or refresh this repository's releases; raises ``ImportProblem``.

        ``report`` hears each stage with a count: releases read so far while
        retrieving, files to write when writing. ``cancelled`` is honoured up
        to the moment writing starts and never after it, since a write stopped
        halfway is exactly the state the rest of this exists to avoid.
        """
        report(ImportStage.RETRIEVING, 0)
        releases = self.source.releases(
            address, lambda count: report(ImportStage.RETRIEVING, count), cancelled
        )
        if not releases:
            raise NoPublishedReleases()
        existing = self.store.load(address)
        names = file_names_for(existing, releases, self.store.present(address))
        on_disk = self.store.digests(address, tuple(names.values()))
        plan = plan_refresh(address, existing, releases, names, on_disk)
        if cancelled():
            raise ImportCancelled()
        report(ImportStage.WRITING, len(plan.writes))
        self.store.commit(address, plan)
        root = self.store.location(address)
        return ImportOutcome(
            root=root,
            newest=os.path.join(root, plan.collection.file_names[0]),
            plan=plan,
            refreshed=existing is not None,
        )
