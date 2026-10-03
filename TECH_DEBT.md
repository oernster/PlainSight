# Technical debt

What is still open, what is deliberately left and what only looks like debt.

Every item here is a behaviour-preserving internal concern. Nothing in this file
reverts a feature or changes how the application behaves for its user. Read it
against `ARCHITECTURE.md` and the structural tests.

## 1. The shortcut writer has no test

`installer/registry.py` writes shortcuts through the shell, with a PowerShell
fallback when the COM bindings are absent from the bundle. Neither path is
tested: both write a real file into the user's own desktop and Start menu.

Both already take the link they write as an argument, so nothing needs
reshaping first: a Windows-only test can point them at a temporary directory
and check that a shortcut lands there aimed at the right target. The fallback
needs the COM import made to fail inside that test to be reached at all.

## 2. Two repository names can share one collection folder

`safe_segment` makes a repository's name safe for a folder, which on Windows
means dropping trailing dots among other things, so `acme/foo` and `acme/foo.`
both land in `github-releases/acme/foo` (measured). Importing the second then
finds a record naming the first: every file is kept as the reader's own, none
of the second repository's releases is written and the record is rewritten to
name the second, so the first's next refresh keeps everything too. Nothing is
lost; releases go missing. Whether GitHub allows names that collide this way
is not checked; until it is, this is a lead rather than a known failure.

Changing `safe_segment` would move existing collections to new folders, so it
is not the fix. The safe one is to refuse an import into a folder whose
readable record names another repository, with its own problem and wording
in the import dialog. Not done in the round that found it: it needs a new
problem type, a change to what `load` reports for a mismatched record and new
dialog text, which is more than a cheap fix.

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

**The read-only guard passes an `open` with one variable argument.** A port
legitimately carries that verb; the external opener asks the desktop to open an
address and touches no file. An `open` given a mode or flag that writes is caught,
as is a `mode=` it cannot read; flagging every `open` would flag that port
and teach the next reader to weaken the guard.

**A document that cannot be read is still listed.** The user neither caused it
nor can fix it from the viewer, so the reason is shown in place of the body
rather than raised as a dialog or hidden.
