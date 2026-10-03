# Testing

How PlainSight is tested: running the checks, reading what they say, what the
gate holds and what it leaves out, the rules a run by hand has to follow and
how a new test or guard is written. The layer rules themselves are in
[ARCHITECTURE.md](ARCHITECTURE.md); setting up the environment the tests run in
is in [DEVELOPMENT.md](DEVELOPMENT.md).

## Running the checks

From the repository root, with the venv active:

```powershell
python -m pytest
python -m black --check .
python -m flake8 .
python -m ruff check .
```

`pytest` alone is the gated run: the options in `pyproject.toml` add the
coverage measurement and the floor. Add `-v` to see each test named as it runs.

**black, flake8 and ruff are not part of the suite.** No test runs them and
there is no CI, so a formatting or lint regression passes `pytest` untouched.
Run all four and read the exit code of each.

**A full run takes under half a minute.** Measured on Windows: 1,022 tests
passed in 12 seconds on 2026-10-02 and in 22 seconds on 2026-10-03. The count
varies by machine: one test is skipped where there is no skills library to
read (see below).

**Read the exit code, never the text.** The run prints the coverage table then
one summary line. A search of the output for a result word is still not safe,
since coverage rows are named after modules. `0` means the tests passed AND the
floor was met; anything else means read the failures above the table.

## What the gate holds

The floor is 100%, by line AND branch (`--cov-branch`,
`--cov-fail-under=100`), over `plainsight.domain` and `plainsight.application`.
Those are the layers a machine can exercise with no filesystem and no toolkit,
so anything short of complete there is a gap nobody chose.

`plainsight.infrastructure`, `plainsight.ui` and the setup program under
`installer/` are tested against real files, a real `QApplication` and real
widgets. They sit outside the floor rather than dragging it down to a
number that means nothing. Read 100% as "100% of the two inner layers".

## Running it by hand

- **No window, provided the platform is unset.** `tests/conftest.py` sets
  `QT_QPA_PLATFORM` to `offscreen` with `setdefault` before any Qt import, so it
  applies only when the variable is not already set. A shell that already has
  it set to something else puts every window on screen.
- **Your settings are never written.** Every test that writes settings builds
  the store over pytest's `tmp_path`. A few tests ask where the real settings
  live, to check the path; they write nothing. This holds by convention: no
  fixture redirects `.plainsight` in your home directory and no guard checks
  it, so a new test has to keep to it.
- **One test reads your skills library.**
  `test_every_skill_on_this_machine_survives_the_round_trip` in
  `tests/domain/test_passage.py` reads every `SKILL.md` under `.claude\skills`
  in your home directory, to hold a property against real documents rather
  than invented ones. It only reads; it is skipped where that folder does
  not exist.
- **Nothing waits on a click.** The few tests that reach a modal call (a
  message box, a dialog's `exec`, the file chooser) replace it with
  `monkeypatch`, so the run never stops for input.

## Where the tests live

`tests/` mirrors the package, one directory a layer:

| Directory | What it tests | Against |
|---|---|---|
| `domain/` | documents, passages, parsing, releases, settings, pure | values built in the test |
| `application/` | the services, opening files, the tree filter, release import, the update check | hand-written fakes (`tests/application/fakes.py`, `release_fakes.py`) |
| `infrastructure/` | the readers for markdown, Word and PDF, the settings and release stores, the GitHub sources | real files in a temporary folder; PDFs built by `pdf_fixtures.py` |
| `ui/` | the main window, the reading pane, the tree, dialogs, focus rings, contrast | a real `QApplication` and real widgets, offscreen |
| `installer/` | the setup program's window, routes and wording | a real `QApplication`, offscreen |
| `structural/` | the rules no single test can see | the source tree itself |

## Writing a test

- **No mocking library; Qt is never mocked.** A port is stood in for by a
  hand-written fake: `tests/application/fakes.py` holds the shared ones
  (`FakeSettingsStore`, `FakeOpener`, `FakeLauncher` and the rest). A modal call
  is replaced with pytest's `monkeypatch` so the run is not left waiting.
- **The window.** `tests/ui/conftest.py` provides the session's one
  `QApplication` and builds the real `MainWindow` over fakes and a temporary
  library; start from it rather than writing another.
- **Nothing outlives its test.** Both `tests/ui/conftest.py` and
  `tests/installer/conftest.py` destroy every widget after each test through
  `tests/qt_teardown.py`. Widgets left alive once survived into the next suite
  and took the run down when it repainted the application stylesheet.

## Guards

A structural test checks the source tree rather than behaviour, so a rule holds
for code nobody has written yet. The suite in `tests/structural/`:

| Guard | Holds |
|---|---|
| `test_layers.py` | the layer directions; the domain reads nothing from outside itself; the application imports no third-party package |
| `test_composition_root.py` | one composition root, the only place an implementation is built, with nothing constructed at import time |
| `test_read_only.py` | each module uses only the write capabilities granted to it by name; no grant outlives its use; a check on source names, with its limits stated in `write_capabilities.py` |
| `test_write_forms.py` | every write form the audit listed (aliased imports, `os.open`, `QFile`, `QImage.save`, `sqlite3`, `subprocess`, `getattr` and the rest) is seen by that check; the reading forms are not |
| `test_readers.py` | every kind of document has a reader of its own and no reader is kept for a kind that does not exist |
| `test_loc_limits.py` | the 400 line cap and the danger band beneath it, the band derived from the cap |
| `test_declared_dependencies.py` | every third-party package and every tool run as a subprocess is declared |
| `test_credits.py` | every declared dependency is credited in About |
| `test_donation_address.py` | the donation address is exactly the one meant, over https, with one home |

**A guard is not trusted until it has been seen to fail.** A new guard is
proved by planting the violation it exists to catch and reading the failure,
then restoring the tree in a `finally` block so an interrupted proof cannot
leave the plant behind. A test written for a defect is run before the fix,
where it has to fail for the reason named, not merely fail.

---

See also [README.md](README.md), [ARCHITECTURE.md](ARCHITECTURE.md) and
[DEVELOPMENT.md](DEVELOPMENT.md).
