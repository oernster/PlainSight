"""The work sequence: what an install, a repair and a removal actually run.

The ladder is weighted by MEASURED time rather than by step count. Weighting by
steps sends the bar to the last notch within a twentieth of a second and leaves
it there, which reads as a bar that never worked.
"""

from __future__ import annotations

import pathlib
from collections.abc import Callable, Iterable
from dataclasses import dataclass

from installer import actions, registry
from installer.plan import InstallPlan
from installer.steplog import StepLog

COMPLETE_PERCENT = 100
NO_PROGRESS = 0

# Weights measured on the reference build: extracting the bundle dominates and
# each shortcut costs about as much as the registry record.
EXTRACT_WEIGHT = 70
REGISTER_WEIGHT = 10
SHORTCUT_WEIGHT = 10


@dataclass(frozen=True, slots=True)
class Step:
    """One step of the ladder: what it is called, what it does, what it costs."""

    name: str
    run: Callable[[], None]
    weight: int


def install_steps(
    plan: InstallPlan, archive: pathlib.Path, log: StepLog
) -> tuple[Step, ...]:
    """Everything an install does, in order."""
    desktop, start_menu = actions.shortcut_paths()
    executable = actions.executable_path(plan.target)

    def extract() -> None:
        log.write(f"extracting {archive} to {plan.target}")
        actions.extract_payload(archive, plan.target)

    def record() -> None:
        log.write("writing the Apps list record")
        registry.register(plan)

    def desktop_shortcut() -> None:
        log.write(f"desktop shortcut: {plan.desktop_shortcut}")
        if plan.desktop_shortcut:
            registry.write_shortcut(desktop, executable)
        else:
            registry.remove_shortcut(desktop)

    def start_menu_shortcut() -> None:
        log.write(f"start menu shortcut: {plan.start_menu_shortcut}")
        if plan.start_menu_shortcut:
            registry.write_shortcut(start_menu, executable)
        else:
            registry.remove_shortcut(start_menu)

    return (
        Step("Unpacking the application", extract, EXTRACT_WEIGHT),
        Step("Recording the install", record, REGISTER_WEIGHT),
        Step("Desktop shortcut", desktop_shortcut, SHORTCUT_WEIGHT),
        Step("Start menu shortcut", start_menu_shortcut, SHORTCUT_WEIGHT),
    )


def uninstall_steps(target: pathlib.Path, log: StepLog) -> tuple[Step, ...]:
    """Everything a removal does, in order."""
    desktop, start_menu = actions.shortcut_paths()

    def remove_shortcuts() -> None:
        log.write("removing the shortcuts")
        registry.remove_shortcut(desktop)
        registry.remove_shortcut(start_menu)

    def forget() -> None:
        log.write("removing the Apps list record")
        registry.unregister()

    def remove_files() -> None:
        log.write(f"removing {target}")
        actions.remove_tree(target)

    return (
        Step("Removing the shortcuts", remove_shortcuts, SHORTCUT_WEIGHT),
        Step("Forgetting the install", forget, REGISTER_WEIGHT),
        Step("Removing the files", remove_files, EXTRACT_WEIGHT),
    )


def ladder(steps: Iterable[Step]) -> tuple[tuple[Step, int], ...]:
    """Each step with the percentage the bar reads once it has finished."""
    listed = tuple(steps)
    total = sum(step.weight for step in listed) or COMPLETE_PERCENT
    reached = NO_PROGRESS
    rungs: list[tuple[Step, int]] = []
    for step in listed:
        reached += step.weight
        rungs.append((step, round(reached * COMPLETE_PERCENT / total)))
    return tuple(rungs)
