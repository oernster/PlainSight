"""Where a skill came from.

The user asked to separate the skills he wrote from the ones he did not.
Authorship is not written down anywhere, so it cannot be read off a file;
origin can. A skill found in the skills folder is his by every signal the
machine has; one found in the plugins tree is not. That is the honest
axis and it is the one grouped on, so a skill someone else wrote that happens
to sit in his own folder is listed among his. Said here rather than left for
a reader to discover.
"""

from __future__ import annotations

from enum import Enum


class SkillOrigin(Enum):
    """The place a skill was read from, in the order the groups are shown."""

    PERSONAL = "Your skills"
    PLUGIN = "Plugin skills"

    @property
    def label(self) -> str:
        """The heading this group is shown under."""
        return self.value

    @property
    def rank(self) -> int:
        """Display order, taken from the order declared above."""
        return tuple(SkillOrigin).index(self)
