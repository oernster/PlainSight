"""Small helpers shared by the delivery scripts.

The Nuitka check serves all three; the rest serve the macOS build.
"""

from __future__ import annotations

import importlib.metadata
import itertools
import shutil
import subprocess
import sys

BREW = "brew"

# The Nuitka the packaged build is written against: the release Stellody moved
# to on 2026-09-13. An older one left in the environment stops the build here,
# rather than a release nobody chose compiling what ships.
NUITKA_MINIMUM = (4, 2, 1)


def section(title: str) -> None:
    """Announce a stage of the build."""
    print(f"\n{title}")


def run(command: list[str], check: bool = True) -> subprocess.CompletedProcess:
    """Run one step, failing the build on a non-zero exit unless told not to."""
    print("  " + " ".join(command))
    completed = subprocess.run(command, check=False)
    if check and completed.returncode != 0:
        raise SystemExit(f"failed with exit {completed.returncode}")
    return completed


def require(tool: str, formula: str | None = None) -> str:
    """The path of a tool, installing it through brew when it is missing."""
    found = shutil.which(tool)
    if found is not None:
        return found
    if shutil.which(BREW) is None:
        raise SystemExit(f"{tool} is not installed and brew is not available")
    run([BREW, "install", formula or tool])
    found = shutil.which(tool)
    if found is None:
        raise SystemExit(f"{tool} is still not on the path after installing it")
    return found


def require_macos() -> None:
    """Stop unless this is macOS; nothing here works anywhere else."""
    if sys.platform != "darwin":
        raise SystemExit("builddmg.py runs on macOS only")


def require_nuitka() -> None:
    """Stop where Nuitka is missing or older than the build is written against."""
    try:
        installed = importlib.metadata.version("nuitka")
    except importlib.metadata.PackageNotFoundError:
        installed = None
    if installed is not None and _release(installed) >= NUITKA_MINIMUM:
        return
    wanted = ".".join(str(number) for number in NUITKA_MINIMUM)
    found = (
        f"Nuitka {installed} is installed" if installed else "Nuitka is not installed"
    )
    raise SystemExit(
        f"{found}; this build needs {wanted} or later:\n"
        "    python -m pip install -r requirements-dev.txt"
    )


def _release(version: str) -> tuple[int, ...]:
    """The numeric release of a version string, '4.2.1rc1' reading as 4.2.1."""
    return tuple(
        int("".join(itertools.takewhile(str.isdigit, part)) or 0)
        for part in version.split(".")
    )
