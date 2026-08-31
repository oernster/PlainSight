"""Where the skills live when the user has not said otherwise.

Every operating system resolves to the same place beneath the home directory,
so there is one rule rather than three. The home directory itself is injected,
which is what makes this testable without an operating system.
"""

from __future__ import annotations

import os

from .ports import PlatformPaths

CLAUDE_DIRECTORY = ".claude"
SKILLS_DIRECTORY = "skills"


def default_skills_root(paths: PlatformPaths) -> str:
    """The default skills root for the user this process is running as."""
    return os.path.join(paths.home_directory(), CLAUDE_DIRECTORY, SKILLS_DIRECTORY)


def effective_skills_root(remembered_root: str, paths: PlatformPaths) -> str:
    """The root to read: what the user chose, else the default."""
    chosen = remembered_root.strip()
    return chosen if chosen else default_skills_root(paths)
