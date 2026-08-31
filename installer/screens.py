"""How each screen is laid out.

An operation never greys the controls in place: setup moves to a different
screen, so the options are not there to be disabled and there is no row of
greyed boxes during an install.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QLabel,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)

from installer import shell
from installer.existing import Existing
from installer.route import Route
from installer.wording import version_line, wording_for

ROUTE_SCREEN = 0
UNINSTALL_SCREEN = 1
RUNNING_SCREEN = 2
PROGRESS_SCREEN = 3
VERDICT_SCREEN = 4

SECTION_GAP_PX = 14
COMPLETE_PERCENT = 100

DESKTOP_LABEL = "Put a shortcut on the desktop"
START_MENU_LABEL = "Add it to the Start menu"

RUNNING_HEADING = "Skills Viewer is open"
RUNNING_LEAD = (
    "The files cannot be replaced while it is running. Close it and setup will "
    "carry on. Cancel instead to close it yourself."
)


@dataclass(frozen=True, slots=True)
class RouteScreen:
    """The first screen: what this run is for, with the choices that shape it."""

    widget: QWidget
    desktop: QCheckBox
    start_menu: QCheckBox
    heading: QLabel
    lead: QLabel
    flow: QLabel


@dataclass(frozen=True, slots=True)
class ProgressScreen:
    """A title, a bar and the step now running."""

    widget: QWidget
    bar: QProgressBar
    step: QLabel


@dataclass(frozen=True, slots=True)
class VerdictScreen:
    """How it ended: one title and one line."""

    widget: QWidget
    title: QLabel
    line: QLabel
    fields: tuple[str, ...] = field(default=())


def _column(parent: QWidget) -> tuple[QWidget, QVBoxLayout]:
    holder = shell.pane(parent)
    column = QVBoxLayout(holder)
    column.setContentsMargins(0, 0, 0, 0)
    column.setSpacing(SECTION_GAP_PX)
    return holder, column


def build_route_screen(parent: QWidget, existing: Existing) -> RouteScreen:
    """The route screen, its options opening on what is already true."""
    holder, column = _column(parent)
    heading = shell.label(holder, "", "Heading")
    flow = shell.label(holder, "", "Flow")
    lead = shell.label(holder, "", "Lead")
    desktop = shell.option(holder, DESKTOP_LABEL, existing.desktop)
    start_menu = shell.option(holder, START_MENU_LABEL, existing.start_menu)
    for widget in (heading, flow, lead, desktop, start_menu):
        column.addWidget(widget)
    return RouteScreen(holder, desktop, start_menu, heading, lead, flow)


def build_uninstall_screen(parent: QWidget) -> QWidget:
    """Removal, reachable from every other screen."""
    holder, column = _column(parent)
    wording = wording_for(Route.UNINSTALL)
    column.addWidget(shell.label(holder, wording.heading, "Heading"))
    column.addWidget(shell.label(holder, wording.lead, "Lead"))
    return holder


def build_running_screen(parent: QWidget) -> QWidget:
    """The application is open and has to close before any file is touched."""
    holder, column = _column(parent)
    column.addWidget(shell.label(holder, RUNNING_HEADING, "Heading"))
    column.addWidget(shell.label(holder, RUNNING_LEAD, "Lead"))
    return holder


def build_progress_screen(parent: QWidget) -> ProgressScreen:
    """A title, a bar and the step now running. No actions at all."""
    holder, column = _column(parent)
    title = shell.label(holder, "Working", "Heading")
    bar = QProgressBar(holder)
    bar.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    bar.setRange(0, COMPLETE_PERCENT)
    step = shell.label(holder, "", "Muted")
    for widget in (title, bar, step):
        column.addWidget(widget)
    return ProgressScreen(holder, bar, step)


def build_verdict_screen(parent: QWidget) -> VerdictScreen:
    """One title and one line, with Close as the only action."""
    holder, column = _column(parent)
    title = shell.label(holder, "", "Heading")
    line = shell.label(holder, "", "Lead")
    column.addWidget(title)
    column.addWidget(line)
    return VerdictScreen(holder, title, line)


def dress_route_screen(
    screen: RouteScreen, route: Route, existing: Existing, version: str
) -> None:
    """Say what this route says, from the one reading of the machine."""
    wording = wording_for(route)
    screen.heading.setText(wording.heading)
    screen.flow.setText(version_line(route, existing.version, version))
    screen.lead.setText(wording.lead)
