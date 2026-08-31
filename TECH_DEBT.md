# Technical debt

What is still open, what is deliberately left and what only looks like debt.

Every item here is a behaviour-preserving internal concern. Nothing in this file
reverts a feature or changes how the application behaves for its user. Read it
against `ARCHITECTURE.md` and the structural tests.

## 1. The LGPL-3.0 licence text is not in the repository

The licence split needs three files: `LICENSE` carrying the overview and the
directory to licence map, `LICENSE-GPL-3.0.txt` and `LICENSE-LGPL-3.0.txt`. Only
the GPL-3.0 text is present, as `LICENSE`.

The official LGPL-3.0 text must be copied in verbatim rather than written from
memory, so this is blocked on that file being fetched and dropped in. Until it
is, the UI licence button has nothing to show and the split is stated in the
plan rather than in the repository.

## 2. The donation address is not yet known

`skillsviewer/version.py` holds `DONATE_URL` as an empty string. Skills Viewer
needs its own payment address, generated for this application; borrowing another
project's would send money against the wrong project.

Blocked on an owner decision. The structural test asserting the address
literally cannot be written until there is an address to assert.

## 3. There is no icon master at the repository root

The seven files in `assets/` are 1254 pixels square. The house pattern is a
single 1024 square RGBA master at the repository root, from which
`generate_icons.py` derives every size, the Windows `.ico`, the macOS `.icns`
and the donate mark. Neither the master nor the generator exists yet.

## 4. The button artwork is loaded at full size

Each of the seven pictures in `assets/` is roughly 1.4MB at 1254 pixels square,
scaled down to a 28 pixel icon at load. It works and it is wasteful.

Resolved by item 3: once `generate_icons.py` exists, the derived button marks
come out of it at the size they are drawn.

## 5. There is no packaging yet

No `buildexe.py`, `buildinstaller.py`, `build_flatpak.sh`, `clean_flatpak.sh` or
`builddmg.py`. The application runs from source with `python -m skillsviewer`.

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
