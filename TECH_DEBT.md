# Technical debt

What is still open, what is deliberately left and what only looks like debt.

Every item here is a behaviour-preserving internal concern. Nothing in this file
reverts a feature or changes how the application behaves for its user. Read it
against `ARCHITECTURE.md` and the structural tests.

## 1. The shortcut writer has no test

`installer/registry.py` writes shortcuts through the shell, with a PowerShell
fallback when the COM bindings are absent from the bundle. Neither path is
tested: both write a real file into the user's own desktop and Start menu.

Worth a temporary-directory test that points the shortcut paths somewhere
harmless, which needs those two functions to take a destination rather than
reading it themselves.

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

**The installer header sizes itself from the title, not the tagline.** The
window grows to fit the title; the tagline is word wrapped, so it has a small
minimum width and never participates in sizing. A short enough product name
therefore leaves the tagline too little room and it breaks onto a second line.
Measured when the name went from thirteen characters to ten: the window shrank
from 826px to 730px and the tagline lost 96px of the 574px it wanted. Left
alone because the obvious fix is wrong: a minimum width taken from the label's
own metrics would be read before the stylesheet is applied, so it would be
taken from the wrong font. The tagline fits with room to spare;
`tests/installer/test_setup_window.py::test_the_tagline_reads_on_a_single_line`
fails the moment that stops being true.

## Not debt (do not "fix" these)

**The read-only guard ignores an attribute called `open`.** A port legitimately
carries that verb; the external opener asks the desktop to open an address and
touches no file. Widening the check to attribute calls would flag that port and
teach the next reader to weaken the guard.

**A document that cannot be read is still listed.** The user neither caused it
nor can fix it from the viewer, so the reason is shown in place of the body
rather than raised as a dialog or hidden.
