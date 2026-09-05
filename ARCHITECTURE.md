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
| No text region takes a ring in any state | `tests/ui/test_focus_rings.py::test_no_text_region_takes_a_ring_in_any_state` |
| No container appears in a focus chain | `tests/ui/test_focus_rings.py::test_no_container_is_in_the_main_window_focus_chain` |
| Each tray's ring order is its drawn order | `tests/ui/test_keyboard_ring.py::test_each_tray_declares_its_own_order_left_to_right_as_drawn` |
| The rendered page is drawn at the size the pane was given | `tests/ui/test_font_size.py::test_the_rendered_page_is_drawn_at_the_size_the_pane_was_given` |
| A torn down widget is destroyed, not merely hidden | `tests/ui/test_qt_teardown.py::test_the_teardown_leaves_nothing_alive` |
| The process setup starts is granted the foreground | `tests/installer/test_launching.py::test_the_started_process_is_granted_the_foreground` |
| The composition root presents rather than shows | `tests/ui/test_main_window.py::test_the_composition_root_presents_rather_than_shows` |
| No folder chosen means no directory is read | `tests/ui/test_first_run.py::test_no_folder_chosen_means_no_directory_is_read` |
| An unrelated folder implies no plugins tree | `tests/application/test_defaults.py::test_an_unrelated_folder_implies_no_plugins_tree_at_all` |
| Opening one file lists no directory | `tests/application/test_open_file.py::test_the_folder_row_is_named_from_the_path_rather_than_listed` |
| Every declared dependency is credited in About | `tests/structural/test_credits.py::test_every_declared_dependency_is_credited` |
| Every kind this application reads has a reader | `tests/structural/test_readers.py::test_every_kind_has_a_reader` |

Every one of these has been proved to bite by planting a violation and reading
the exit code.

## Paths are strings in the domain

The domain holds a document's path and a folder's path as plain strings
rather than as path objects. It reads nothing from disk, so it has no use for a
path object's behaviour; importing one would put a filesystem module inside the
layer that is defined by not having one. Infrastructure converts at the
boundary, which is the only place a path is ever acted on.

## Read only, as a structural fact

The application never writes to a document. That is not left
to discipline: `tests/structural/test_read_only.py` names the one module allowed
to write at all, the settings store, then asserts that no other module in the
package calls a writing operation. Editing a document is exclusively the
external editor's job.

The check has one stated limit. It matches the builtin `open` by name but not an
attribute called `open`, because a port legitimately carries that verb: the
external opener asks the desktop to open an address and touches no file.

## Components

### Domain

- `parsing`: splits a document into its frontmatter fields and its prose. Pure
  string work over text somebody else read.
- `document`: one document, its `DocumentKind` and the `failure` it carries when
  the file could not be read. A document with a failure is still listed, because
  the user neither caused it nor can fix it from the viewer. `DocumentKind` is
  the single home for which file suffixes are read at all; it also settles
  whether a kind declares frontmatter and how its text reaches the reading
  surface. Discovery, rendering and softening each ask it rather than holding a
  list of their own, so adding a kind is adding a member and nothing else. A
  kind may answer to more than one suffix, since `.htm` and `.html` name the
  same thing everywhere outside this application.
- `Presentation`: the three ways a body becomes what the surface shows. Text
  laid out for the page, text that is its own layout, then text that is already
  the thing the surface renders. This was a flag while there were two of them;
  HTML is the third and had nowhere to go in a boolean.
- `library`: the tree. A `Folder` holds its subfolders and its documents, each
  ordered case insensitively with folders first; a `Library` holds the roots.
  The single ordering rule lives here.
- `settings`: what is remembered between runs, plus the editor choice and its
  validation.

### Application

`ports` declares the seams as Protocols: `DocumentRepository`, `SettingsStore`,
`EditorLauncher`, `ExternalOpener`, `PathProbe`, `PlatformPaths`,
`AssetLocator`, `DocumentRenderer`, `DocumentReader` and `ReleaseSource`. `ReleaseSource` returns a release type
declared in `update`, which imports `ports` in turn, so the annotation is
imported under `TYPE_CHECKING` alone; a runtime import there would close a
circle.

`defaults` holds the rules about which folder is read; there is
deliberately no rule that picks one. `chosen_root` returns what the user
chose or nothing at all; `browse_from` names where the chooser opens, which
is the Claude skills folder before anything has been taken. Those are two
different questions and separating them is the whole point: a folder offered
in a dialog the user is standing in front of has not been read, while a
folder nobody offered is never read at all. It is also the only place in the package that
knows the name of any particular tool. The home directory is injected through
`PlatformPaths`, which is what makes it testable with no operating system.

`LibraryService` is frozen and holds only its injected dependencies. It
answers questions rather than holding answers: `can_open_in_editor` is the enable
predicate for the view in editor control, so the user interface asks rather than
works it out. That predicate needs three things to be true at once: a document
is selected, an editor was chosen and that editor is still where it was.

`update` holds the whole update decision above both the toolkit and the network:
the release types, the comparison, the platform-to-file mapping, `UpdateService`
and `outcome_for`. Every part of it is pure, so the one thing the check has to
get right, when to speak and when to stay quiet, is settled by a table of cases
rather than by a running application. The comparison reads dotted integers only:
anything it cannot read compares as not newer, so a malformed tag can never
raise a prompt.

### Infrastructure

- `document_repository`: walks a directory tree and reports it as a `Folder`.
  Every file whose suffix names a `DocumentKind` is a document; every directory
  holding one at any depth is a folder; hidden and cache directories are passed
  over. A branch leading to no document is not reported at all, so every branch
  the reader can open leads somewhere. A directory that cannot be listed costs
  only itself rather than the whole tree.

  What a file of a given kind says about itself is not its business; it walks
  the tree, decides what is a document at all, records what each file was and
  asks a reader for the rest.

  A listing does not keep the bodies it read. What it keeps is what a document
  says about itself, whether it can be read at all and a fingerprint of the
  file; `read_body` fetches the text when a document is actually opened.
  Measured over the skills tree, a library of 59 documents held 42.2KB rather
  than the 859.6KB those files hold on disk; one document opened in 0.2ms.
  What that bought arrived with PDF. Measured over forty PDFs of twelve pages
  each: listing them takes 7ms where extracting them all takes 515ms. The
  library is re-read every time the window comes forward, so that difference is
  paid on every activation rather than once.
- `document_reader`: one reader per kind, told which kind it serves rather than
  asked to recognise what it was given. `TextDocumentReader` covers the three
  text kinds, which differ only in whether a leading fence is a block of fields.
  Its two halves are apart because they cost differently: `summarise` runs for
  every document beneath a chosen folder and
  must stay cheap, while `read_body` runs for the one document that was opened
  and may be as dear as its kind demands. A kind that must be extracted rather
  than decoded brings its own reader and this one never learns of it.

  The readers are named in the composition root, written out rather than
  derived from the enumeration, so a kind added without a reader is a gap
  somebody fills on purpose instead of one filled silently with the wrong
  reader. `tests/structural/test_readers.py` holds that map to covering every
  kind there is.
- `word_reader`: a Word document, converted to Markdown at the boundary rather
  than anywhere further in, so the softening, the readable column and the
  renderer stay exactly as they were and none of them learns that this document
  arrived as a zip full of XML. Headings, paragraphs, lists, tables and the
  emphasis inside them cross; presentation does not, since none of it survives
  the reading pane anyway. The body is walked over its own XML rather than over
  `paragraphs` and `tables`, which are two collections each in document order
  only within itself: read that way a table lands after every paragraph in the
  file rather than between the two it sits between.
- `pdf_reader`: a PDF, read as the text that can be got out of it and presented
  verbatim. A PDF describes a page rather than a document, so what comes back is
  a reconstruction: two columns interleave and a table arrives as its cells in
  drawing order. Softening it would make that worse by running the columns
  together, which is why this kind is shown as typed. Three failures are told
  apart because they want different words: a locked file, a file that is not a
  PDF and a file holding no text a machine can reach, which is what a scan is.
- Both of those readers catch every exception when opening a file, which is
  deliberate and marked with a stated reason rather than a bare suppression.
  They parse a file somebody else chose, several layers down in a library with
  no contract about what it raises: a zip whose content type map is merely the
  wrong shape was measured arriving as an `AttributeError` from lxml. A list of
  the types seen so far is a list the next broken file gets to extend; a
  reader must not take the application down over a file that was clicked.
- `settings_store`: versioned JSON, written atomically through a temporary file
  and a replace, so a process that dies halfway leaves the previous settings
  intact. Its `FORMAT_VERSION` is the file's own number and has nothing to do
  with the application's. That separation is what a stable release does and does
  not promise: the application version is free to move without the settings a
  user has accumulated needing anything done to them; the format may be revised
  on its own number when it has to be.
- `platform`: the home directory and the path probe.
- `renderer`: rendering through the `markdown` package for a kind that is laid
  out; into an escaped preformatted block for one kept as typed; untouched for
  one that is already HTML. Passing plain text through a Markdown renderer would
  silently rewrite it: a line of hyphens becomes a heading rule and the author's
  own line breaks disappear. Passing HTML through a parser would lose whatever
  the parser did not understand, once on every pass, to produce the document it
  started with.
- `update_source`: the one place the application opens a connection of its own.
  It asks the GitHub releases endpoint for the latest published release of this
  repository and nothing else. That endpoint returns only a published,
  non-draft, non-prerelease release, so a tag pushed mid-development is
  invisible here by the endpoint's own contract rather than by a check made
  after the fact. The opener is injected, so no test leaves the machine; every
  failure answers None and there are no retries.
- `resources`: finds the bundled assets and the `VERSION` file across
  development, a Nuitka bundle and a flatpak. Nuitka sets `__file__` to the
  module's place inside the bundle, so walking up from it reaches the bundle
  root under a compiled build exactly as it reaches the repository root in
  development; one rule serves both. The launcher's own directory is tried
  last, which is what answers the flatpak. It carries no `sys._MEIPASS`
  branch, because nothing here builds with PyInstaller.

### User interface

Two trays around a split body, exactly as design plan part 2 describes.

- `theme`: two `Palette` values and the one stylesheet template built from
  either, together with a text size. The three sizes derive from one base and
  one step rather than being written out separately, so they cannot drift
  apart; the rendered document declares no size of its own, so it takes this and
  scales with everything else. The ring model has three states and no more: nothing at rest, green
  while hovered or focused and enabled, permanent red while disabled. The accent
  is never a ring. A ring belongs to a control, so neither the tree nor the
  reading pane paints one in any state: both are regions the pointer rests
  inside rather than controls it points at. The pane carried one until a click
  on the text drew a rectangle round the whole page. It was admitted through an
  exception list in the guard whose own comment called
  `QTextBrowser:enabled:focus` an object-name selector that could not reach a
  subclass; it is a class selector and reached every pane in the application.
  There is no exception list now. `ring` and `danger` are named per palette rather than shared,
  since a pastel green that reads on near-black is weak on white.
- `keyboard_nav`: one `KeyboardNavigator` installed as an application event
  filter, driving a ring recomputed live on every move. `NeutralStart` is the
  zero-size sink that absorbs the window's first focus.
- `auto_scroller`: the reading cycle, one per surface, with the constants on the
  class rather than per dialog. A surface beneath a modal is frozen rather than
  suspended; `suspend` is itself gated on the surface being active, so a modal's
  own reset cannot be read as a reader taking hold.
- `document_view`: a redraw forced by a change of colour or of text size keeps
  the reader's place, taken as an offset into the text rather than a scroll
  position. A character survives a reflow where a pixel does not: at another
  size the same fraction of the page is different words. The place is taken by
  `remember_place` BEFORE the stylesheet is applied, because applying it
  reflows the page under the reader; asked afterwards the pane reports where it
  was thrown to, which was measured capturing the wrong paragraph.
  The document it builds is given the pane's own font before its text, which is
  the price of building one rather than filling the widget's. A built
  `QTextDocument` starts on the APPLICATION default font and `setDocument` does
  not correct it, so the text size reached the widget and the readable column
  re-measured from it while the words stayed at 9pt through all three settings:
  the page re-centred rather than growing. The font goes on before the text
  because it decides the layout. `tests/ui/test_font_size.py` compares the two
  fonts rather than the stylesheet, since it was the widget and its document
  that disagreed.
  `wear` gives it a palette and the window re-renders after, because a rendered
  document keeps the colours it was rendered under. A frontmatter value longer
  than a few lines is lifted out of the header and given its own section after
  the body, so a value running to thousands of characters cannot bury the text
  the reader opened.
- `top_tray` and `bottom_tray`: each declares `ring_stops()` left to right as
  drawn, so the ring's order is never inferred from a layout walk. The text
  size control sits right of the editor controls behind a `QFrame` hairline
  which, being a container, takes no focus and appears in no ring. Both cycling
  controls wear the state they would move to rather than the current one; both
  put it on through the same `_wear` helper. The help
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
- `library_tree`: one stop, walked with Up and Down, with internal cell tab
  walking turned off so Tab leaves in a single press. It mirrors the folders on
  disk, a document row carrying the file's own name so a reader can find the
  same file again in a dialogue. Enter or Space opens and closes a folder,
  since the horizontal arrows step the window's ring everywhere and cannot also
  be the tree's own keys. A folder is remembered by its path rather than by its
  label, because two folders can share a name. The arrow is drawn at runtime in
  the palette's colour rather than styled: Qt renders a stylesheet triangle as
  nothing at all and draws a branch arrow only from an image file, while a text
  glyph would rest on a font holding it, which this harness cannot verify. The
  toolkit's own indicator is suppressed by a `QTreeWidget::branch` rule in the
  theme, since `setRootIsDecorated(False)` clears it on top level rows alone;
  every folder below a root otherwise drew a second, smaller arrow beside ours.
  Restoring a selection never opens a shut folder, because Qt expands ancestors
  to reach a row and would otherwise undo the reader's decision on every
  re-read.
- Nothing is ever selected that the reader did not select. There is deliberately
  no fallback to the first row: the library is re-read on every activation of
  the window, so a fallback would choose for them again and again; the pane
  reads itself down the page, so it would be scrolling through a document
  nobody opened. An empty pane saying "Select a document" is the opening state.
- `library_tree` and `document_view` together: a document already on screen and
  unchanged is not drawn again. Each re-read used to send the page
  back to the top, so leaving to look something up lost your place and
  scrolling looked as though it had been ignored. A document compares by value
  and carries a fingerprint of the file it came from, so one edited on disk is a
  different document and is redrawn as it should be.
- `reading_pane`: one home for how a scrolling text region behaves. It attaches
  the reading cycle, gates its own focus on overflow (a page that fits scrolls
  nowhere, so it is no stop at all) and answers Home, End, Ctrl+Home and
  Ctrl+End. Qt binds only the bare pair on a read-only browser, measured rather
  than assumed, so the two chords a reader reaches for first would otherwise do
  nothing. The document pane and both dialogs sit on it, which is what stops the
  three drifting apart.
  It also holds the text column to a readable line length, so a wide window
  buys margins rather than longer lines; text that arrived hard wrapped, a
  licence being the case, is left exactly as it came. The typography lives in
  `document_style` beside the colours, because a document's own paragraphs can be
  enormous: the longest measured runs past four thousand characters unbroken.
  Nothing here may rewrite what an author wrote, so the levers are the ones a
  reader owns, open line spacing, air between blocks and a capped measure.
  It is reachable by a click as well as by Tab while it overflows, since Tab
  alone meant clicking the text you were reading did not focus it and the keys
  that move around a document went somewhere else and looked broken.
- `reading_choice`: what is being read, a folder the reader chose or one file
  they opened, together with how it is read again. The two are one concern
  rather than two, because a re-read has to know which of them it is looking
  at. Reported as the Open file button not working: the file did open, then the
  activation re-read replaced it with the chosen folder before the reader saw
  it, since closing a chooser is exactly what activates the window. A single
  opened file is now re-read as itself, so both answers keep the same promise
  that what is on screen is what is on disk now. A file that has gone since it
  was opened falls back to the folder rather than leaving a tree describing
  nothing; choosing a folder afterwards drops the file, because that is the
  reader saying they want the folder.
- `about_dialog`, `licence_dialog`, `widgets`: the dialogs and the pieces they
  share, all on the `FirstStopDialog` base.

`passage.soften` is the answer to a wall of text that typography alone cannot
reach. An over-long passage is shown in groups of whole sentences with a gap
between them; an inventory with no sentence ends in it gets a second pass at
the divisions its author did write, the end of a bracketed entry and the
semicolon. Nothing is added, removed or reordered; that is mechanical rather
than promised: a test takes the breaks back out and requires the
original text character for character, over every document on the machine as well
as over invented ones. Measured over the real library, the longest block a
reader meets falls from 5604 characters to 1893; blocks past 1500 fall from 26
to 4. It runs in the pane rather than anywhere nearer the file, because it
is a decision about presenting text and never about storing it.

Every colour pairing that carries text is held to the WCAG AA ratio by a test in
the application as well as in the setup program. Three were under it and each
looked deliberate: the selected row, every heading in a rendered document and a
link in the light theme. The dark theme carries a separate selection fill
because one accent cannot do both jobs there; a heading on the panel wants the
lighter violet and white on the selected row wants the darker one.

A dialog is destroyed when it closes rather than left parented and hidden.
Measured before that: ten openings of a licence left ten dialogs alive with ten
forty millisecond reading cycles still ticking behind the window. The reading
cycle also watches only its own surface now; listening to the application for
focus reached back to a surface that could already be gone and took the process
down on teardown.

## Nothing is read that nobody asked for

Reading a person's files is theirs to authorise. Until a folder is chosen,
`LibraryService.load` returns an empty `Library` and asks the repository for
nothing at all, so a fresh install walks no home directory. On a machine where
permissions are explicit, an unasked scan is a rummage through directories
nobody offered; it is no better on one where they are not.

Fetching a body when a document is opened put a question where the body used
to answer it. The reading pane leaves a document that has not changed exactly
as it is, half read and at the place the reader had reached; it decides that
by value: the library is re-read on every activation, so the document it
is handed has to compare equal to the one on screen. The body carried that
weight by being part of the value. A `fingerprint`, the file's size and
modification time, carries it now at the cost of one look at the directory
entry rather than a read of every file. The pane is handed something to call
rather than text; it calls that only where it is going to redraw, so a document
left alone is never read off disk again.

Opening a single document obeys the same rule from the other end.
`DocumentRepository.read_document` calls no directory listing at all: the
folder row a reader sees is named from the path rather than looked into, so
one file opened is one file read. `dialogs.readable_filter` builds the
chooser's filter from `readable_suffixes`, so what a chooser offers cannot
drift from what discovery accepts.

The same rule governs the second root. `LibraryService` combines the chosen
folder with the plugins tree beside it only where the chosen folder is
itself a Claude skills folder, which `plugins_root_for` decides by reading two
directory names rather than the home directory, so a relocated `.claude` still
works. Anywhere else it returns nothing and exactly one directory is read: the
one the user picked. The rule used to be the sibling called `plugins` whatever
was chosen, which meant picking `C:\Work\Notes` walked `C:\Work\plugins`.

A tree that is not there contributes no root at all rather than a heading over
nothing; nor does one leading to no document at any depth. Which roots exist is
therefore a property of the library rather than of the widget showing it.

`MainWindow.apply_appearance` does three things in one call: repaint the
application stylesheet, re-face the toggle and re-render the open document. Split
apart, the toggle can be left showing the mode just departed, which invites a
second press; the document then keeps the old palette's colours too.

The user interface reaches the application layer and the domain only. Bundled
artwork is found through the `AssetLocator` port rather than by importing
infrastructure, which is how the layer guard caught the first version of the
trays.

## The setup program

`installer/` is a second application in the same repository, not a part of the
first: nothing in `plainsight/` imports it and nothing in it imports the
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
- Starting the application at the end is two halves and neither works alone.
  Windows refuses the foreground to a process that does not already hold it,
  so setup, which does hold it, grants the right to the process it has just
  started; the application asks for it through `MainWindow.present`, which
  raises and activates rather than merely showing. Reported after a fresh
  install with only the second half missing: the window opened behind
  everything and did no more than flash on the taskbar. Setup still closes
  only after the start returns, since closing first hands the foreground back
  to whatever was behind it. Neither half can be checked offscreen, so both
  are tested at the mechanism: that the grant reaches the process actually
  started, then that the composition root calls `present` rather than `show`.

The read-only invariant is about the application, not the
setup program: an installer writes files by definition. What it never touches
is a folder of documents; it writes only under `%LOCALAPPDATA%\Programs` and `HKCU`.

## Quality enforcement

The coverage floor is 100% branch coverage over `domain` plus `application`, the
layers reachable with no filesystem, no Qt and no editor.

Infrastructure, the user interface and the setup program all carry real tests,
against a temporary directory and against a real offscreen `QApplication`. All
three sit outside the floor rather than dragging it to a number that would mean
nothing.

`black --check`, `flake8`, `ruff check` and the pytest gate are four separate
commands, each read by exit code. None of them is wired into the suite as an
assertion.

Both Qt suites tear their widgets down through `tests/qt_teardown.py`, in one
place rather than one copy each. Closing a window hides it; `deleteLater` only
posts a DeferredDelete event that `processEvents` does not deliver outside a
running event loop, so the teardown they each had destroyed nothing at all.
Every widget either suite built stayed in the application; the run then died
with an access violation inside `QApplication.setStyleSheet`, which has to walk
all of them: five times in fifteen. Fixed, the same suite ran twenty five times with
no crash; reinstating the old teardown in the setup program's fixtures alone
brought it back at ten in twenty, which is what makes this the cause rather than
a correlation. It also took the suite from about four minutes to five seconds.
`tests/ui/test_qt_teardown.py` holds the guard.
