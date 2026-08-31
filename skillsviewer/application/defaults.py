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
PLUGINS_DIRECTORY = "plugins"


def default_skills_root(paths: PlatformPaths) -> str:
    """The default skills root for the user this process is running as."""
    return os.path.join(paths.home_directory(), CLAUDE_DIRECTORY, SKILLS_DIRECTORY)


def effective_skills_root(remembered_root: str, paths: PlatformPaths) -> str:
    """The root to read: what the user chose, else the default."""
    chosen = remembered_root.strip()
    return chosen if chosen else default_skills_root(paths)


def plugins_root_for(skills_root: str) -> str:
    """The plugins tree that sits beside a skills folder.

    Both live under the same ``.claude`` directory, so the plugins tree is
    found from the skills root rather than guessed at separately. Browse
    somewhere with no plugins beside it and there is simply nothing to read,
    which is what makes an unrelated folder show one list and no grouping.
    """
    return os.path.join(
        os.path.dirname(os.path.normpath(skills_root)), PLUGINS_DIRECTORY
    )
