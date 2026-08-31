"""The setup window: it owns the state and says what is shown.

The screens own layout, wording owns text and performing owns the work. What is
here is only which of those is on screen and what the footer offers.
"""

from __future__ import annotations

import sys

from PySide6.QtCore import QSize, Qt, QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QApplication,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from installer import actions, launching, running, screens, shell, theme
from installer.bundled import (
    DARK_MODE_NAME,
    LIGHT_MODE_NAME,
    appearance_mark,
    archive_path,
    licence_path,
    mark_path,
    read_version,
)
from installer.existing import Existing, look
from installer.footer import DANGER, PRIMARY, Action, Footer
from installer.performing import install_steps, ladder, uninstall_steps
from installer.plan import InstallPlan
from installer.route import Route, route_for
from installer.steplog import StepLog
from installer.wording import PRODUCT, verdict_line, verdict_title, wording_for

UNINSTALL_FLAG = "--uninstall"
LICENCE_LABEL = "Licence"
TO_LIGHT_TOOLTIP = "Switch to the light appearance"
TO_DARK_TOOLTIP = "Switch to the dark appearance"
CLOSE_LABEL = "Close"
CANCEL_LABEL = "Cancel"
REMOVE_LABEL = "Remove"
REINSTALL_LABEL = "Reinstall"
CLOSE_AND_CONTINUE_LABEL = "Close it and continue"
STEP_DELAY_MS = 30


class SetupWindow(QWidget):
    """The three bands, with one screen showing in the middle of them."""

    def __init__(self, uninstalling: bool) -> None:
        super().__init__()
        self.setObjectName("Shell")
        self.setWindowTitle(f"{PRODUCT} Setup")
        self.resize(theme.WINDOW_WIDTH_PX, theme.WINDOW_HEIGHT_PX)
        mark = mark_path()
        if mark is not None:
            self.setWindowIcon(QIcon(str(mark)))

        self.version = read_version()
        self.existing: Existing = look()
        self.route = route_for(self.existing.version, self.version, uninstalling)
        self.log = StepLog()
        self.palette_choice = theme.DARK
        self._pending: tuple[tuple[object, int], ...] = ()
        self._succeeded = True

        self.licence_button = self._link(LICENCE_LABEL, self.show_licence)
        self.theme_button = self._mark_button(self.switch_appearance)
        self.stack = QStackedWidget(self)
        self.stack.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.footer = Footer(self)
        self._build()
        self.apply_appearance()
        self.show_route()

    def _link(self, label: str, on_click) -> QPushButton:
        button = QPushButton(label, self)
        button.setObjectName("Link")
        button.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        button.clicked.connect(on_click)
        return button

    def _mark_button(self, on_click) -> QPushButton:
        """The appearance toggle: artwork, not a text pill."""
        button = QPushButton(self)
        button.setObjectName("Mark")
        button.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        button.setFixedSize(theme.MARK_BUTTON_PX, theme.MARK_BUTTON_PX)
        button.setIconSize(QSize(theme.MARK_ICON_PX, theme.MARK_ICON_PX))
        button.clicked.connect(on_click)
        return button

    def _build(self) -> None:
        """The three bands, with the body centred rather than packed up."""
        self.route_screen = screens.build_route_screen(self.stack, self.existing)
        self.uninstall_screen = screens.build_uninstall_screen(self.stack)
        self.running_screen = screens.build_running_screen(self.stack)
        self.progress_screen = screens.build_progress_screen(self.stack)
        self.verdict_screen = screens.build_verdict_screen(self.stack)
        for screen in (
            self.route_screen.widget,
            self.uninstall_screen,
            self.running_screen,
            self.progress_screen.widget,
            self.verdict_screen.widget,
        ):
            self.stack.addWidget(screen)

        column = QVBoxLayout(self)
        margin = theme.BODY_MARGIN_PX
        column.setContentsMargins(margin, margin, margin, margin)
        column.setSpacing(theme.BAND_GAP_PX)
        column.addWidget(
            shell.header(self, mark_path(), (self.licence_button, self.theme_button))
        )
        column.addWidget(shell.rule(self))
        column.addStretch()
        column.addWidget(self.stack)
        column.addStretch()
        column.addWidget(shell.rule(self))
        column.addWidget(self.footer)

        self._neutral = shell.NeutralStart(self)

    def apply_appearance(self) -> None:
        """Repaint and re-face the toggle together, so it never lags.

        The toggle wears the appearance it would move TO, so the sun appears
        while you are in the dark.
        """
        self.setStyleSheet(theme.stylesheet(self.palette_choice))
        moving_to_light = self.palette_choice is theme.DARK
        name = LIGHT_MODE_NAME if moving_to_light else DARK_MODE_NAME
        tooltip = TO_LIGHT_TOOLTIP if moving_to_light else TO_DARK_TOOLTIP
        found = appearance_mark(name)
        if found is not None:
            self.theme_button.setIcon(QIcon(str(found)))
        self.theme_button.setToolTip(tooltip)
        self.theme_button.setAccessibleName(tooltip)

    def switch_appearance(self) -> None:
        """Swap the palette, then say what the toggle would move to next."""
        self.palette_choice = (
            theme.LIGHT if self.palette_choice is theme.DARK else theme.DARK
        )
        self.apply_appearance()

    def showEvent(self, event: object) -> None:
        """Neutral start: no control wears a ring until one is asked for."""
        super().showEvent(event)  # type: ignore[arg-type]
        self._neutral.absorb()

    def show_route(self) -> None:
        """The route screen, dressed for the one reading of the machine."""
        screens.dress_route_screen(
            self.route_screen, self.route, self.existing, self.version
        )
        self.stack.setCurrentIndex(screens.ROUTE_SCREEN)
        wording = wording_for(self.route)
        offered = [Action(wording.go_ahead, self.begin, PRIMARY)]
        if self.route is Route.MANAGE:
            offered.append(Action(REINSTALL_LABEL, self.begin))
        if self.existing.installed:
            offered.append(Action(REMOVE_LABEL, self.show_uninstall, DANGER))
        offered.append(Action(CLOSE_LABEL, self.close))
        self.footer.show_actions(offered)

    def show_uninstall(self) -> None:
        """Removal is a screen reachable from everywhere, not a route."""
        self.stack.setCurrentIndex(screens.UNINSTALL_SCREEN)
        self.footer.show_actions(
            (
                Action(
                    wording_for(Route.UNINSTALL).go_ahead, self.begin_removal, DANGER
                ),
                Action(CANCEL_LABEL, self.show_route),
            )
        )

    def begin(self) -> None:
        """Ask whether the application is open BEFORE touching any file."""
        if running.is_running():
            self.stack.setCurrentIndex(screens.RUNNING_SCREEN)
            self.footer.show_actions(
                (
                    Action(CLOSE_AND_CONTINUE_LABEL, self.close_and_continue, PRIMARY),
                    Action(CANCEL_LABEL, self.show_route),
                )
            )
            return
        self.perform(install_steps(self.current_plan(), archive_path(), self.log))

    def close_and_continue(self) -> None:
        """Close the application, then carry on with the same work."""
        running.close_it()
        self.perform(install_steps(self.current_plan(), archive_path(), self.log))

    def begin_removal(self) -> None:
        """Remove what is installed, wherever the Apps list says it is."""
        self.perform(uninstall_steps(self.existing.location, self.log))

    def current_plan(self) -> InstallPlan:
        """What this install will do, from the boxes as they stand."""
        target = (
            self.existing.location
            if self.existing.installed
            else actions.default_target()
        )
        return InstallPlan(
            target=target,
            version=self.version,
            desktop_shortcut=self.route_screen.desktop.isChecked(),
            start_menu_shortcut=self.route_screen.start_menu.isChecked(),
        )

    def perform(self, steps) -> None:
        """Move to the progress screen and walk the ladder from there.

        The progress screen offers no actions at all: a screen with nothing
        safe to offer offers nothing.
        """
        self._pending = ladder(steps)
        self._succeeded = True
        self.stack.setCurrentIndex(screens.PROGRESS_SCREEN)
        self.footer.show_actions(())
        QTimer.singleShot(STEP_DELAY_MS, self.next_step)

    def next_step(self) -> None:
        """Run one step, then schedule the next or reach the verdict."""
        if not self._pending:
            self.show_verdict()
            return
        (step, reached), self._pending = self._pending[0], self._pending[1:]
        self.progress_screen.step.setText(step.name)
        try:
            step.run()
        except Exception as failure:  # noqa: BLE001 - the verdict is the only exit
            self.log.write(f"failed: {failure}")
            self._succeeded = False
            self.show_verdict()
            return
        self.progress_screen.bar.setValue(reached)
        QTimer.singleShot(STEP_DELAY_MS, self.next_step)

    def show_verdict(self) -> None:
        """Every path ends here: a title, a line and Close."""
        self.verdict_screen.title.setText(verdict_title(self.route, self._succeeded))
        self.verdict_screen.line.setText(
            verdict_line(self._succeeded, str(self.log.path))
        )
        self.stack.setCurrentIndex(screens.VERDICT_SCREEN)
        offered = [Action(CLOSE_LABEL, self.close, PRIMARY)]
        if self._succeeded and self.route is not Route.UNINSTALL:
            offered.insert(
                0, Action(f"Start {PRODUCT}", self.launch_and_close, PRIMARY)
            )
        self.footer.show_actions(offered)

    def launch_and_close(self) -> None:
        """Bring the new window forward; only then close setup."""
        launching.start(actions.executable_path(self.current_plan().target))
        self.close()

    def show_licence(self) -> None:
        """The one licence setup carries: the Qt LGPL it is covered by."""
        from installer.licence import LicenceWindow

        LicenceWindow(licence_path(), self).show()


def main(argv: list[str] | None = None) -> int:
    """Start the setup program."""
    arguments = sys.argv if argv is None else argv
    application = QApplication(list(arguments))
    window = SetupWindow(uninstalling=UNINSTALL_FLAG in arguments)
    window.show()
    return application.exec()


if __name__ == "__main__":
    raise SystemExit(main())
