"""Hand-written stand-ins for the release import's two ports."""

from __future__ import annotations

from collections.abc import Callable

from plainsight.application.release_import import CollectionWriteFailed
from plainsight.domain.release import Release
from plainsight.domain.release_collection import (
    RefreshPlan,
    ReleaseCollection,
    digest_of,
)
from plainsight.domain.repository_address import RepositoryAddress


class FakeReleaseSource:
    """Answers the releases it was given; raises the problem if given one.

    ``asked`` records every repository asked about, which is how a test proves
    that an address refused before the network was never asked about at all.
    """

    def __init__(
        self,
        releases: tuple[Release, ...] = (),
        problem: Exception | None = None,
        before_answer: Callable[[], None] | None = None,
    ) -> None:
        self.releases_given = releases
        self.problem = problem
        self.before_answer = before_answer
        self.asked: list[RepositoryAddress] = []

    def releases(
        self,
        address: RepositoryAddress,
        on_page: Callable[[int], None],
        cancelled: Callable[[], bool],
    ) -> tuple[Release, ...]:
        self.asked.append(address)
        if self.before_answer is not None:
            self.before_answer()
        if self.problem is not None:
            raise self.problem
        on_page(len(self.releases_given))
        return self.releases_given


class FakeCollectionStore:
    """A collection held in memory: its record, its files and what was asked."""

    def __init__(self, location: str = "/imports/oernster/PlainSight") -> None:
        self.where = location
        self.collection: ReleaseCollection | None = None
        self.files: dict[str, str] = {}
        self.commits: list[RefreshPlan] = []
        self.fail_commit = False

    def location(self, address: RepositoryAddress) -> str:
        return self.where

    def load(self, address: RepositoryAddress) -> ReleaseCollection | None:
        return self.collection

    def digests(
        self, address: RepositoryAddress, file_names: tuple[str, ...]
    ) -> dict[str, str | None]:
        return {
            name: digest_of(self.files[name]) if name in self.files else None
            for name in file_names
        }

    def commit(self, address: RepositoryAddress, plan: RefreshPlan) -> None:
        if self.fail_commit:
            raise CollectionWriteFailed("disk full")
        self.commits.append(plan)
        for write in plan.writes:
            self.files[write.file_name] = write.text
        self.collection = plan.collection
