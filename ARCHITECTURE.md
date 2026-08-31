# Architecture

## The invariant

```
UI -> Application -> Domain <- Infrastructure
```

The domain knows nothing of files, screens or clocks. The application states the
use cases in terms of the domain and a set of ports. Infrastructure implements
those ports. The user interface is a client of the application only.

Each invariant below names the test that enforces it. A rule with no test is a
wish.

| Invariant | Enforced by |
|---|---|
| No layer imports a layer it may not see | `tests/structural/test_layers.py::test_no_layer_imports_a_layer_it_may_not_see` |
| The domain imports no filesystem, clock, logging or threading module | `tests/structural/test_layers.py::test_the_domain_reads_nothing_from_outside_itself` |
| The application imports no third-party package | `tests/structural/test_layers.py::test_the_application_layer_imports_no_third_party_package` |
| No module exceeds 400 lines | `tests/structural/test_loc_limits.py::test_no_module_is_over_the_cap` |
| No module sits in the 381 to 399 danger band | `tests/structural/test_loc_limits.py::test_no_module_sits_in_the_danger_band` |
| Nothing but the settings store writes anything | `tests/structural/test_read_only.py::test_only_the_settings_store_writes_anything` |
| Only the composition root builds an implementation | `tests/structural/test_composition_root.py::test_only_the_composition_root_builds_an_implementation` |
| The composition root builds every implementation | `tests/structural/test_composition_root.py::test_the_composition_root_builds_every_implementation` |
| Every third-party package used is declared | `tests/structural/test_declared_dependencies.py::test_every_package_used_is_declared` |
| Every tool invoked as a subprocess is declared | `tests/structural/test_declared_dependencies.py::test_every_tool_invoked_as_a_subprocess_is_declared` |
| The donation address is exactly the one intended | `tests/structural/test_donation_address.py::test_the_address_is_exactly_this` |
| The donation address appears exactly once | `tests/structural/test_donation_address.py::test_the_address_has_one_home` |
| Nothing is constructed at import time | `tests/structural/test_composition_root.py::test_nothing_is_constructed_at_import_time` |
| No container class carries a ring rule | `tests/ui/test_focus_rings.py::test_no_container_class_carries_a_ring_rule` |
| The item view takes no hover ring | `tests/ui/test_focus_rings.py::test_the_item_view_takes_no_hover_ring` |
| The item view takes no focus ring either | `tests/ui/test_focus_rings.py::test_the_item_view_takes_no_focus_ring_either` |
| No container appears in a focus chain | `tests/ui/test_focus_rings.py::test_no_container_is_in_the_main_window_focus_chain` |
| Each tray's ring order is its drawn order | `tests/ui/test_keyboard_ring.py::test_each_tray_declares_its_own_order_left_to_right_as_drawn` |

Every one of these has been proved to bite by planting a violation and reading
the exit code.

## Paths are strings in the domain

The domain holds a skill's directory, document and companions as plain strings
rather than as path objects. It reads nothing from disk, so it has no use for a
path object's behaviour; importing one would put a filesystem module inside the
layer that is defined by not having one. Infrastructure converts at the
boundary, which is the only place a path is ever acted on.

## Read only, as a structural fact

Design plan 13.1 says the application never writes to a skill. That is not left
to discipline: `tests/structural/test_read_only.py` names the one module allowed
to write at all, the settings store, then asserts that no other module in the
package calls a writing operation. Editing a skill is exclusively the external
editor's job.

The check has one stated limit. It matches the builtin `open` by name but not an
attribute called `open`, because a port legitimately carries that verb: the
external opener asks the desktop to open an address and touches no file.

## Components

### Domain

- `skill_document`: splits a `SKILL.md` into its declared fields and its prose.
  Pure string work over text somebody else read.
- `skill`: one skill, including the `failure` it carries when its document could
  not be read. A skill with a failure is still listed, because the user neither
  caused it nor can fix it from the viewer.
- `catalogue`: the skills of one root, in display order. The single ordering rule
  lives here.
- `settings`: what is remembered between runs, plus the editor choice and its
  validation.

### Application

`ports` declares the seams as Protocols: `SkillRepository`, `SettingsStore`,
`EditorLauncher`, `ExternalOpener`, `PathProbe`, `PlatformPaths`,
`MarkdownRenderer` and `ReleaseSource`. `ReleaseSource` returns a release type
declared in `update`, which imports `ports` in turn, so the annotation is
imported under `TYPE_CHECKING` alone; a runtime import there would close a
circle.

`defaults` holds the one rule for where skills live when the user has not said
otherwise. The home directory is injected through `PlatformPaths`, which is what
makes the per-operating-system default testable with no operating system.

`SkillLibraryService` is frozen and holds only its injected dependencies. It
answers questions rather than holding answers: `can_open_in_editor` is the enable
predicate for the view in editor control, so the user interface asks rather than
works it out. That predicate needs three things to be true at once: a skill is
selected, an editor was chosen and that editor is still where it was.

`update` holds the whole update decision above both the toolkit and the network:
the release types, the comparison, the platform-to-file mapping, `UpdateService`
and `outcome_for`. Every part of it is pure, so the one thing the check has to
get right, when to speak and when to stay quiet, is settled by a table of cases
rather than by a running application. The comparison reads dotted integers only:
anything it cannot read compares as not newer, so a malformed tag can never
raise a prompt.

### Infrastructure

- `skill_repository`: applies the discovery rules of design plan section 1.
- `settings_store`: versioned JSON, written atomically through a temporary file
  and a replace, so a process that dies halfway leaves the previous settings
  intact.
- `platform`: the home directory and the path probe.
- `markdown_renderer`: rendering through the `markdown` package.
- `update_source`: the one place the application opens a connection of its own.
  It asks the GitHub releases endpoint for the latest published release of this
  repository and nothing else. That endpoint returns only a published,
  non-draft, non-prerelease release, so a tag pushed mid-development is
  invisible here by the endpoint's own contract rather than by a check made
  after the fact. The opener is injected, so no test leaves the machine; every
  failure answers None and there are no retries.
- `resources`: finds the bundled assets and the `VERSION` file across
  development, a PyInstaller bundle (`sys._MEIPASS`) and a flatpak, where the
  launcher's own path locates them. It carries no Nuitka branch, because
  nothing here builds with Nuitka.

### User interface

Two trays around a split body, exactly as design plan part 2 describes.

- `theme`: two `Palette` values and the one stylesheet template built from
  either. The ring model has three states and no more: nothing at rest, green
  while hovered or focused and enabled, permanent red while disabled. The accent
  is never a ring. `ring` and `danger` are named per palette rather than shared,
  since a pastel green that reads on near-black is weak on white.
- `keyboard_nav`: one `KeyboardNavigator` installed as an application event
  filter, driving a ring recomputed live on every move. `NeutralStart` is the
  zero-size sink that absorbs the window's first focus.
- `auto_scroller`: the reading cycle, one per surface, with the constants on the
  class rather than per dialog. A surface beneath a modal is frozen rather than
  suspended; `suspend` is itself gated on the surface being active, so a modal's
  own reset cannot be read as a reader taking hold.
- `top_tray` and `bottom_tray`: each declares `ring_stops()` left to right as
  drawn, so the ring's order is never inferred from a layout walk. The help
  control drops a menu holding About and Check for Updates. It is popped by
  hand rather than set on the button, because a button carrying a menu grows an
  arrow indicator and every other control in that tray is a picture and nothing
  else.
- `update_check`: the controller that runs a check off the interface thread and
  reports what it found. Its result crosses back on a signal connected to a
  bound method of an object living on the interface thread, which is the whole
  reason the class exists: a signal connected to a bare callable runs in the
  sender's thread; no widget may be touched from there. `MainWindow` takes
  the update service as an optional dependency, so a test can build a window
  that asks nothing of the network; the composition root always supplies one.
- `skill_tree`: one stop, walked with Up and Down, with internal cell tab
  walking turned off so Tab leaves in a single press. Skills sit under a heading
  for the origin they came from and Enter or Space opens and closes one, since
  the horizontal arrows step the window's ring everywhere and cannot also be the
  tree's own keys. The arrow is drawn at runtime in the palette's colour rather
  than styled: Qt renders a stylesheet triangle as nothing at all and draws a
  branch arrow only from an image file, while a text glyph would rest on a font
  holding it, which this harness cannot verify. Restoring a selection never
  opens a shut heading, because Qt expands ancestors to reach a row and would
  otherwise undo the reader's decision on every re-read.
- A skill already on screen and unchanged is not drawn again. The library is
  re-read on every activation of the window; each re-read used to send the page
  back to the top, so leaving to look something up lost your place and
  scrolling looked as though it had been ignored. A skill compares by value, so
  a document edited on disk is a different skill and is redrawn as it should be.
- `reading_pane`: one home for how a scrolling text region behaves. It attaches
  the reading cycle, gates its own focus on overflow (a page that fits scrolls
  nowhere, so it is no stop at all) and answers Home, End, Ctrl+Home and
  Ctrl+End. Qt binds only the bare pair on a read-only browser, measured rather
  than assumed, so the two chords a reader reaches for first would otherwise do
  nothing. The skill pane and both dialogs sit on it, which is what stops the
  three drifting apart.
  It also holds the text column to a readable line length, so a wide window
  buys margins rather than longer lines; text that arrived hard wrapped, a
  licence being the case, is left exactly as it came. The typography lives in
  `document_style` beside the colours, because a skill's own paragraphs can be
  enormous: the longest measured runs past four thousand characters unbroken.
  Nothing here may rewrite what an author wrote, so the levers are the ones a
  reader owns, open line spacing, air between blocks and a capped measure.
  It is reachable by a click as well as by Tab while it overflows, since Tab
  alone meant clicking the text you were reading did not focus it and the keys
  that move around a document went somewhere else and looked broken.
- `skill_view`: the skill on that pane. `wear` gives it a palette; the window
  re-renders after, because a rendered document keeps the colours it was
  rendered under. A frontmatter value longer than a few lines is lifted out of
  the header and given its own section after the body, so a value running to
  thousands of characters cannot bury the skill the reader opened.
- `about_dialog`, `licence_dialog`, `widgets`: the dialogs and the pieces they
  share, all on the `FirstStopDialog` base.

`passage.soften` is the answer to a wall of text that typography alone cannot
reach. An over-long passage is shown in groups of whole sentences with a gap
between them; an inventory with no sentence ends in it gets a second pass at
the divisions its author did write, the end of a bracketed entry and the
semicolon. Nothing is added, removed or reordered; that is mechanical rather
than promised: a test takes the breaks back out and requires the
original text character for character, over every skill on the machine as well
as over invented ones. Measured over the real library, the longest block a
reader meets falls from 5604 characters to 1893; blocks past 1500 fall from 26
to 4. It runs in the pane rather than anywhere nearer the file, because it
is a decision about presenting text and never about storing it.

Every colour pairing that carries text is held to the WCAG AA ratio by a test in
the application as well as in the setup program. Three were under it and each
looked deliberate: the selected row, every heading in a rendered skill and a
link in the light theme. The dark theme carries a separate selection fill
because one accent cannot do both jobs there; a heading on the panel wants the
lighter violet and white on the selected row wants the darker one.

A dialog is destroyed when it closes rather than left parented and hidden.
Measured before that: ten openings of a licence left ten dialogs alive with ten
forty millisecond reading cycles still ticking behind the window. The reading
cycle also watches only its own surface now; listening to the application for
focus reached back to a surface that could already be gone and took the process
down on teardown.

`SkillOrigin` in the domain names where a skill was read from and the order the
groups are shown in; `SkillCatalogue.groups` gathers by it and leaves out an
origin that contributed nothing, so a machine with no plugins sees one list. The
axis is origin rather than authorship because authorship is recorded nowhere,
which means a skill someone else wrote inside the user's own folder is listed
among theirs. `SkillLibraryService` reads both places and combines them, so
grouping is a property of the library rather than of the widget showing it.

`MainWindow.apply_appearance` does three things in one call: repaint the
application stylesheet, re-face the toggle and re-render the open skill. Split
apart, the toggle can be left showing the mode just departed, which invites a
second press; the document then keeps the old palette's colours too.

The user interface reaches the application layer and the domain only. Bundled
artwork is found through the `AssetLocator` port rather than by importing
infrastructure, which is how the layer guard caught the first version of the
trays.

## The setup program

`installer/` is a second application in the same repository, not a part of the
first: nothing in `skillsviewer/` imports it and nothing in it imports the
application. It follows the house setup model.

- `route` and `wording` are pure, so every state setup can be in is a test
  rather than a screenshot. One reading of the machine decides the screen, its
  heading, the options on it and the buttons under it, which is what stops
  those four drifting apart.
- An operation moves to a different SCREEN rather than greying the controls
  where they are, so there is no row of dead boxes during an install.
- The footer is rebuilt per screen from a list of actions. The progress screen
  offers nothing at all.
- The bar is weighted by measured time rather than by step count, since even
  weighting sends it to the last notch within a twentieth of a second.
- The archive is fenced as a whole before any entry is written, so a crafted
  archive cannot write half its contents before one is caught climbing out.
- Every path ends in a verdict; a step log is flushed as it goes.
- The tagline belongs to the header rather than to the name above it, so the
  controls sit inside the names column and the tagline is given the whole width
  beside the mark. Boxed under the name it took the name's width, broke a line
  early and stranded its last word, while the room it needed sat unused beside
  the controls. The focus order is unchanged by that, measured either side.
- Every colour pairing that carries text is held to the WCAG AA ratio by a test
  rather than judged by eye. The primary button drew the accent on the selection
  fill at 3.34 to 1 and the destructive button its red at 3.99, both under the
  4.5 that is readable and both looking deliberate. The primary button now has a
  token of its own, a blue named per theme, since one light enough for the dark
  fill would vanish on the pale one.
- The licence is a text button and the appearance toggle is artwork, which is
  the deliberate asymmetry of the house header. Both marks are staged beside the
  payload rather than left inside the bundle the setup program has not extracted
  yet. A test asserts every mark the window reads is one the staging step
  carries.

The read-only invariant of design plan 13.1 is about the application, not the
setup program: an installer writes files by definition. What it never touches
is a skills root; it writes only under `%LOCALAPPDATA%\Programs` and `HKCU`.

## Quality enforcement

The coverage floor is 100% over `domain` plus `application`, the layers reachable
with no filesystem, no Qt and no editor.

Infrastructure, the user interface and the setup program all carry real tests,
against a temporary directory and against a real offscreen `QApplication`. All
three sit outside the floor rather than dragging it to a number that would mean
nothing.

`black --check`, `flake8`, `ruff check` and the pytest gate are four separate
commands, each read by exit code. None of them is wired into the suite as an
assertion.
