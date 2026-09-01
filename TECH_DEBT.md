# Technical debt

What is still open, what is deliberately left and what only looks like debt.

Every item here is a behaviour-preserving internal concern. Nothing in this file
reverts a feature or changes how the application behaves for its user. Read it
against `ARCHITECTURE.md` and the structural tests.

## 1. Nothing has been built on the Nuitka toolchain

The delivery scripts moved from PyInstaller to Nuitka and not one of them has
been run since. `buildexe.py`, `buildinstaller.py` and `builddmg.py` are all
written against the house recipe and none of the three has produced an artefact,
so every claim about them rests on the flag list rather than on a build.

Two things in particular are unproven rather than merely untested. The bundle
resolves its assets by walking up from `__file__`, which is correct for a Nuitka
standalone bundle by Nuitka's own documented behaviour and has not been seen to
work here. The Qt exclusions moved from PyInstaller's `--exclude-module` to
Nuitka's `--nofollow-import-to`; the resulting bundle size has not been
measured against the 726MB that made them necessary.

Blocked on a build-and-launch pass, which the sandbox must not do.

## 2. The setup program has never been run

The setup program has only been driven offscreen through its window: its
screens, its footer and its route are tested; no install, repair or removal has
been performed on a real machine. An install from the PyInstaller-built setup
program was performed once, which is how the reading-place fix was confirmed on
the installed application, so the install path is not wholly unexercised. That
evidence belongs to the old toolchain and does not carry over; see item 1.

Blocked on a build-and-launch pass, which the sandbox must not do: it would
write to `%LOCALAPPDATA%` and `HKCU` on this machine.

## 3. The shortcut writer has no test

`installer/registry.py` writes shortcuts through the shell, with a PowerShell
fallback when the COM bindings are absent from the bundle. Neither path is
tested: both write a real file into the user's own desktop and Start menu.

Worth a temporary-directory test that points the shortcut paths somewhere
harmless, which needs those two functions to take a destination rather than
reading it themselves.

## 4. The suite crashes intermittently, so a green run proves less than it looks

Under `QT_QPA_PLATFORM=offscreen` the run sometimes dies with a Windows access
violation partway through `tests/ui/test_reading_place.py`. The stack is the
same every time: `MainWindow.apply_appearance` at the line that hands the built
stylesheet to `QApplication.setStyleSheet`, reached from the window's own
constructor.

What is measured, over five full runs. It crashed twice and passed three times.
Running `tests/ui/test_reading_place.py` on its own passed three times out of
three, so it needs the state a full run has accumulated by that point rather
than anything in the file. It has been seen on PySide6 6.11.0 and on 6.11.2, so
it is not a version. It crashed before the reading pane's ring rule was removed
and before the move to Nuitka, so it is older than both.

What is NOT known is the cause. A stylesheet cannot be reparsed into an access
violation on its own, so the suspicion is a widget destroyed earlier in the run
and still reachable when the sheet is reapplied, which is the same shape as the
teardown crash already fixed once by having the reading cycle watch only its own
surface. That is a hypothesis and nothing here has tested it.

The cost is not the lost run. It is that a green suite is now weak evidence: a
crash reads as a regression when it is this; a real failure after the crash
point is never reached at all. The next measurement is to make it reproducible
rather than to fix it, by running the UI tests with the window count and the
destroyed-window teardown reported per test, so the run that crashes can be told
from the ones that do not.

## Looks like debt, not worth touching

**Paths held as strings in the domain.** It reads as a missed abstraction and is
not one: the domain reads nothing from disk, so a path object would buy nothing
and its import would break the purity rule. See `ARCHITECTURE.md`.

**Infrastructure and the user interface outside the coverage floor.**
Deliberate. The floor covers the layers reachable with no filesystem, no Qt and
no editor, holding those at 100%. Both of the others carry real tests, against a
temporary directory and against a real offscreen `QApplication`; extending the
floor to them would mean either a weaker number over everything or a list of
exclusions that makes the number meaningless.

## Not debt (do not "fix" these)

**The read-only guard ignores an attribute called `open`.** A port legitimately
carries that verb; the external opener asks the desktop to open an address and
touches no file. Widening the check to attribute calls would flag that port and
teach the next reader to weaken the guard.

**A skill whose document cannot be read is still listed.** Design plan 12.2. The
user neither caused it nor can fix it from the viewer, so the reason is shown in
place of the body rather than raised as a dialog or hidden.
