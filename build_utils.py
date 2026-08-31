"""Small helpers shared by the macOS delivery script."""

from __future__ import annotations

import shutil
import subprocess
import sys

BREW = "brew"


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
