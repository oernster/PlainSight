# PlainSight: plan and design

## What it does

Reads a folder of documents, shows it as the tree it is on disk,
renders the document you select and hands editing to an editor the user chooses.
It reads nothing until the user chooses a folder; the chooser opens on the
Claude skills folder, which is an offer rather than a scan. It is not a text
editor and it never writes to a document.

## Identity

- GitHub repository: `PlainSight`
- Application name: PlainSight
- Author: Oliver Ernster
- Tech stack: Python plus PySide6
- UI licence: LGPL-3.0
- Model licence: GPL-3.0

## Scope, stated once

Any folder of Markdown, plain text, HTML, Word or PDF files. The Claude skills
folder is the default and the origin of the application, not a limit on it. Not affiliated
with Anthropic and not endorsed by them; the About dialog says so.

---

# Part 1: requirements

## 1. What a document is

1.1 A document is a **file whose suffix names a kind the application reads**.
Five kinds ship: Markdown (`.md`), plain text (`.txt`), HTML (`.html`, `.htm`),
Word (`.docx`) and PDF (`.pdf`). The set lives in one place, the `DocumentKind`
enumeration, so adding a kind is adding a member and a reader for it.

1.2 Only Markdown carries a frontmatter block. How a kind reaches the reading
surface is one of three answers rather than a flag: laid out for the page
(Markdown, plus Word once its reader has made it Markdown), kept as typed
(plain text, plus PDF, whose text carries the page's own line breaks) or already
the HTML the surface renders. Text kept as typed is shown exactly as it was: three
hyphens in a text file are three hyphens.

1.3 A directory holding a document at any depth is a **folder** and is listed as
one. A branch leading to no document at all is not listed, so every branch the
reader can open leads somewhere.

1.4 Ignored on sight: any directory whose name begins with `.` and any named
`__pycache__`. Both are present in the author's tree (`.ruff_cache`,
`__pycache__`). A directory that cannot be listed at all is passed over rather
than raised on: one unreadable folder must not cost the reader the whole tree.

1.5 A document's row carries **the file's own name**, so a reader who finds
something here can find the same file again in a dialogue or a shell. Where a
document declares a `name` in its frontmatter, that heads the reading pane
instead, so a skill opens under the name it calls itself while still listing as
the `SKILL.md` it is. Its `description`, where present, is the row's tooltip.

## 2. Where documents come from

2.1 **Nothing is read until the user chooses a folder.** There is no default
root and no first-run scan: a fresh install opens on an empty tree and an
invitation, having looked at nothing on the machine. Reading a person's files
is theirs to authorise; on a system where permissions are explicit an unasked
walk of a home directory is a rummage through directories nobody offered.

2.2 A browse button on the far left of the top tray is how a folder is chosen.
The chooser **opens** at the place below, all three resolving to the same one:

| OS | Where the chooser opens |
|---|---|
| Windows | `%USERPROFILE%\.claude\skills` |
| macOS | `~/.claude/skills` |
| Linux | `~/.claude/skills` |

That is a starting place for a dialog the user is standing in front of, never a
folder read on its own account. It keeps the common case to one click without
taking the choice away. It is also where this application began; `defaults` is
the only module in the package that knows the name of any particular tool. Once
a folder has been taken the chooser opens there instead. The choice persists
between runs.

2.3 A chosen root that does not exist opens with an empty tree and a message
inviting the browse button; so does one that holds no document at any depth.
Neither is an error and neither gets a dialog. Both are said differently from
the state in 2.1, since a folder that was read and held nothing is not the same
fact as a machine that has not been read at all.

2.4 **The plugins tree is read as well, where the chosen folder implies one.**
A Claude skills folder has a `plugins` directory for a sibling under the same
`.claude` directory; a reader who points at one plainly means that pair.
Any other folder implies nothing about its neighbours, so exactly one directory
is read: the one the user picked. The test is the two directory names rather
than the home directory, so a relocated `.claude` still works.

2.5 **Each tree is a root of its own** in the left pane, named for its own
directory. A tree that is not there or that leads to no document contributes
no root at all rather than a heading over nothing. That keeps the
skills a reader wrote and the ones that arrived with a plugin apart without the
application needing a notion of authorship, which is written down nowhere and
cannot be read off a file.

2.6 **One document on its own.** A second button immediately right of the
browse one opens a single file, offering the suffixes `DocumentKind`
declares so the chooser cannot drift from what discovery accepts. It reads
that file and lists no directory: the folder row is named from the path, so
the reader sees where it came from while whatever sits beside it stays
unread. It is selected at once, which is not the auto-selection 3.3 refuses,
since a reader who names one file has already chosen it. The choice is not
remembered, so the next run opens on the folder that was chosen.

2.7 **Still out of scope:** anything that is not a file under a chosen tree.
Several skills a Claude session offers are supplied by the tool rather than
stored on disk, so nothing here can see them and nothing here pretends to.

## 3. Displaying a document

3.1 The left pane is a **tree mirroring the folders on disk**, folders before
documents and each group ordered case insensitively. Every folder opens and
closes on its own arrow and carries a count of what it holds, so a shut branch
says whether it is worth opening. Exactly one document is displayed at a time.

3.2 Layout is that tree on the left and the rendered document on the right.
Sequential presentation alone was rejected: reaching the eleventh document would
mean stepping through ten.

3.3 **Nothing is selected until the reader selects it.** There is deliberately no
fallback to the first row. The library is re-read whenever the window comes back
to the front, so a fallback would choose again on every return; the pane
reads itself down the page, so the application would be scrolling through a
document nobody opened. The opening state is an empty pane saying so.

3.4 Markdown is **rendered**, not shown as source, in a readable proportional
font with monospace for fenced code. Three runtime dependencies serve the kinds
it reads, each credited in About: `markdown` (BSD-3-Clause) for rendering,
`python-docx` (MIT) for Word and `pypdf` (BSD-3-Clause) for PDF. Plain text goes
into a preformatted block with its own characters escaped, since passing it
through a Markdown renderer would silently rewrite it.

3.5 The frontmatter block is stripped before rendering and surfaced as a compact
header above the body: name, description, then any other fields the document
declares.

3.6 Selecting a different document replaces the pane's content and returns the
auto-scroll cycle to its start hold rather than continuing mid-descent.

## 4. Auto-scroll (the `scroll` skill)

4.1 Applied to the rendered document pane, the About dialog, the UI licence dialog
and the model licence dialog. All four are read through rather than acted on,
which is the boundary that skill draws.

4.2 **Not** applied to the library tree, which is a surface to act on.

4.3 One set of constants on the scroller class, never per surface: 40ms tick,
5000ms start hold, 1px per two ticks descending, 5000ms bottom hold, 15px per tick
rewind, 2000ms top hold, 2500ms resume after manual input.

4.4 The overflow guard means attaching it to a short document is free and correct.

## 5. Help and About

5.0 An appearance toggle immediately left of the help button. It wears the
application's own light and dark artwork and shows the appearance it would move
**to**, so the sun appears while you are in the dark. Repainting, re-facing the
toggle and re-rendering the open document all happen in one call, so it can never
be left showing the mode just departed. The choice persists between runs; each
palette names its own ring and danger tokens rather than sharing one pair.

5.1 A help and about button on the far right of the top tray.

5.2 About shows the application icon, the name, the version, "Oliver Ernster",
the copyright with its symbol, the dual licence line and credit where credit is
due: every real dependency named with its licence.

5.3 About states plainly that PlainSight reads nothing until a folder is
chosen; it names the Claude skills folder as where the chooser opens. It states just as
plainly that it is not affiliated with or endorsed by Anthropic.

## 6. Choosing an editor

6.1 A choose editor button in the top tray, immediately right of the browse
button.

6.2 It opens a file chooser for the editor executable. The choice persists between
runs, recorded as a path plus a display name.

## 7. Viewing in the editor

7.1 A view in editor button in the top tray, immediately right of the choose
editor button.

7.2 It launches the chosen editor with the selected document as the file
to edit. This application is not a text editor replacement.

7.3 It is **disabled by default**. The enable predicate, stated so the keyboard
ring can honour it: enabled when a document is selected **and** an editor is chosen
**and** the chosen editor path still exists. Otherwise disabled, which means
skipped by the focus ring and painting the permanent red ring.

7.4 A launch the desktop refuses puts a message in the status bar. Silence would
leave the user pressing a button that appears to do nothing.

## 8. Keyboard navigation (the `keeb` skill, with `noborderfocus`)

8.1 One explicit ring, recomputed live, wrapping at both ends. Tab and Right step
forward; Shift+Tab and Left step back, tested first so the arrows step the ring
everywhere.

8.2 Ring order, which is reading order:

1. browse folder
2. choose editor
3. view in editor (skipped while disabled)
4. text size
5. appearance toggle
6. help and about
7. the library tree (one stop; Up and Down walk the rows)
8. the rendered pane, **only while it overflows**
9. donate
10. UI licence
11. model licence

then wrapping back to the browse button.

8.3 Both trays declare their own `ring_stops()` left to right as drawn, so the
collector never infers order from a layout walk.

8.4 The main window starts neutral. Every dialog opens already focused on its
first enabled, visible, focusable control.

8.5 Ring colours: no ring at rest, green while hovered or focused and enabled,
permanent red while disabled. The brand accent is never a ring.

8.6 No container is a stop and no container paints a ring. The library tree is an
item view, so it rings in **no** state; its current row is the indicator. The
rendered pane rings in **no** state either. It is a region the pointer rests
inside rather than a control it points at, so a rectangle round the words being
read marks no target; clicking the text to use the document keys drew it every
time, which is how it was reported. It remains a stop while it overflows, since
a long document has to be readable from the keyboard.

## 9. Donations (the `donate` skill)

9.1 A donate button at the far left of the bottom tray, before the app's own
controls.

9.2 The application never fetches the page. It hands the address to the desktop
and the browser does the asking, so the local-first guarantee is untouched by the
button existing.

9.3 One home for the address, a named constant beside the rest of the identity.
The artwork is derived from a single master by the icon generator.

9.4 The tooltip says the browser opens, since the picture alone does not.

9.5 The artwork is in place: `assets/donate-master.png` is the master and the
icon generator derives `assets/donate.png` from it, cropped to its artwork and
scaled by height. The address is PlainSight's own, generated for this
application rather than borrowed from another. A structural test asserts it
literally, asserts its scheme and asserts it appears exactly once.

## 10. UI licence

10.1 A UI licence button in the bottom tray, immediately right of donate, with its
own icon asset.

10.2 It shows LGPL-3.0 in a dialog with auto-scroll applied, sized to the width of
its own text rather than to a hardcoded minimum.

## 11. Model licence

11.1 A model licence button in the bottom tray, immediately right of the UI
licence button, with its own icon asset.

11.2 It shows GPL-3.0 in a dialog with auto-scroll applied, sized the same way.

## 12. Freshness and failure

12.1 The library is re-read when the window is activated. A user who leaves to
edit a document and comes back sees current content; one added or removed while
away appears or disappears. No file watcher, no polling thread.

12.2 A file that cannot be decoded is still listed; so is one whose
frontmatter is malformed. The failure is shown in the pane rather than raised as
a dialog: the user did not cause it and cannot fix it from here.

## 13. Read only, as an invariant

13.1 The application never writes to any path beneath a chosen root. Editing is
exclusively the external editor's job.

13.2 This is enforced by a structural test rather than by convention, in the same
spirit as the no-network test in `postal-gambit`.

## 14. Telling the user a newer release exists

14.1 The help control in the top tray drops a menu of two: About PlainSight,
then Check for Updates. There is no menu bar to hang the second on and the tray
is where the actions already live.

14.2 The check asks the GitHub releases endpoint for the latest published
release of this repository and nothing else. That endpoint answers only with a
published, non-draft, non-prerelease release, so a tag pushed mid-development
cannot raise a prompt. Nothing about the user goes with the question.

14.3 It runs a few seconds after the window shows, then once a day, always off
the interface thread with a five second limit and no retries. A check nobody
asked for speaks only when there is something to download; one the user asked
for reports every outcome, including that it could not reach GitHub.

14.4 A newer release offers three answers: Download, Skip This Version, Later.
Download hands the file for this operating system to the desktop, falling back
to the release page; the application fetches nothing itself. Skip remembers that
one release tag, so the next release still reaches the user.

14.5 This is the one connection the application opens of its own accord, so
every claim to the contrary in the README, the release notes and the code
comments is corrected in the same change rather than left to be found.

## 15. Text size

15.1 Three sizes, medium then large then extra large, stepped by one button in
the top tray and wrapping back to medium. A cycle rather than a continuous
scale, since the control is a single button and the set has to be walkable in a
moment.

15.2 The button sits to the right of the view in editor control, behind a
hairline separator that keeps the editor controls together as a group. The
separator is a container, so it takes no focus and appears in no ring.

15.3 It wears the size it would move to rather than the size in force, exactly
as the appearance toggle does, so the picture answers what pressing it will do.

15.4 The size lives in the one stylesheet the application is painted from and
the rendered document declares no size of its own, so a change reaches the
trays, the tree and the document being read together. It is remembered between
runs beside the appearance.

15.5 A change of colour or of size redraws the page but does not move the
reader: they are put back on the words they were on. The place is an offset
into the text rather than a scroll position, since at another size the same
point down the page is different words. It is taken before the stylesheet
changes, because applying it has already reflowed the page.

## 16. Coming to the front when it starts

16.1 The window opens in front of what is already on screen and takes the
keyboard, rather than opening behind it. `MainWindow.present` shows, raises and
activates; the composition root calls that and never a bare `show`.

16.2 Asking is only half of it on Windows, which refuses the foreground to a
process that does not already hold it. The setup program holds it at the moment
it starts the application, so it grants the right to the process it has just
started, then closes only after that returns. Closing first hands the foreground
back to whatever was behind it.

16.3 Neither half can be settled by an offscreen harness, which sees no stacking
order and no real activation. Both are tested at the mechanism instead: that the
grant reaches the process actually started, then that the composition root
presents rather than shows.

---

# Part 2: design

## Architecture invariant

`UI -> Application -> Domain <- Infrastructure`, enforced by structural tests.

## Domain (stdlib only, no I/O, no clock)

Frozen dataclasses with `slots=True`, `tuple[...]` over `list`.

- `ParsedDocument`: the parse result of a document's text, holding `frontmatter`
  and `body`. Splitting the two is pure string work, so it lives here.
- `DocumentKind`: which file suffixes are read at all, whether a kind declares
  frontmatter and how its text reaches the reading surface. One home for all
  three. A kind may answer to more than one suffix, since `.htm` and `.html`
  name the same thing.
- `Presentation`: the three ways a body becomes what the surface shows: laid out
  for the page, kept as typed or already the HTML the surface renders.
- `Document`: file name, path, kind, declared name, description, the failure it
  carries when the file could not be read and a `fingerprint` of the file.
  Validates in `__post_init__`. It holds no body: the text is fetched when a
  document is opened; the fingerprint is what makes a document still compare
  unequal to the same file edited since.
- `DocumentSummary`: what a listing knows about a document without reading all
  of it. Deliberately carries no text.
- `DocumentBody`: a document's text, else the reason there is none. The reason
  travels with the absence rather than being worked out from it, since a locked
  file and a missing one want different words in front of a reader.
- `Folder`: a directory's subfolders and documents, each ordered case
  insensitively with folders first, plus the recursive `document_count`.
- `Library`: the roots being read, with `by_path()` and the walk in drawn order.
- `Settings`: what is remembered between runs, holding `EditorChoice` (path plus
  display name, validating that the path is non-empty), `Appearance`, `FontSize`
  and the skipped update tag.
- `passage.soften`: breaking a wall of text at divisions its author already
  wrote. Pure string work, adding and removing nothing.

## Application (domain plus stdlib only)

Ports, all Protocols:

- `DocumentRepository`: `read_folder(root) -> Folder | None`,
  `read_document(path) -> Document | None`, `read_body(path) -> DocumentBody`
- `DocumentReader`: `summarise(path) -> DocumentSummary`,
  `read_body(path) -> DocumentBody`. One per kind, chosen by kind rather than
  asked to recognise anything. The two halves are apart because they cost
  differently: summarising runs for every document beneath a chosen folder,
  while reading a body runs for the one document that was opened.
- `SettingsStore`: `load() -> Settings`, `save(settings)`
- `EditorLauncher`: `launch(editor, target) -> bool`
- `ExternalOpener`: `open(address) -> bool`
- `PathProbe`: `exists(path) -> bool`
- `PlatformPaths`: `home_directory() -> str`,
  `program_directories() -> tuple[str, ...]`, `system_directory() -> str`
- `AssetLocator`: `find(name) -> str | None`
- `DocumentRenderer`: `render(body, kind) -> str`
- `ReleaseSource`: `latest_release() -> ReleaseInfo | None`

Services:

- `LibraryService`, frozen, holding its injected dependencies. It owns which
  root is active, which document is current and whether the editor can be
  launched.
  The enable predicate of 7.3 lives here, so the UI asks a question rather than
  computing one.
- `defaults`, pure functions over an injected paths provider, so the per-OS
  behaviour is unit-testable with no operating system involved. There is
  deliberately no function that picks a root: `chosen_root` returns what the
  user chose or nothing at all, while `browse_from` names where the chooser
  opens. Separating those two is the whole point of 2.1. Beside them,
  `plugins_root_for` decides whether a chosen folder implies the sibling tree
  of 2.4, while `default_editor` finds the machine's own editor.

## Infrastructure

`FileSystemDocumentRepository` (the walk and the ignore rules of section 1,
holding a reader per kind and knowing how to read none of them itself),
`TextDocumentReader` for the three text kinds, `WordDocumentReader` turning a
Word document into Markdown at the boundary, `PdfDocumentReader` taking the
text out of a PDF and telling its three failures apart,
`JsonSettingsStore` (atomic write by temp file plus `os.replace`, versioned
`{"version": 1, ...}`), `DesktopEditorLauncher` (`QProcess.startDetached`),
`QtExternalOpener` (`QDesktopServices.openUrl`), `DocumentHtmlRenderer`, plus
`resources.py` carrying `find_asset`, `read_version` and the `BundledAssets`
adapter, so assets resolve under development, a Nuitka bundle and Flatpak
alike.

## UI

```
top tray:    [folder] [choose editor] [view in editor] | [size] .. [light/dark] [help/about]
body:        library tree (left)          |  rendered document (right)
bottom tray: [donate] [UI licence] [model licence] ..............
```

One `AutoScroller` class carrying the canon constants. One `KeyboardNavigator`
installed as an application event filter, driving the ring of section 8. A theme
module holding semantic tokens, with `ring` and `danger` named per theme so the
three-state colour model holds by construction.

Dialogs: `AboutDialog`, plus one `LicenceDialog(title, path, parent)` reused by
both licence buttons, each derived from the first-stop dialog base.

## Assets

The master is `plainsight.png` at the repository root, square RGBA at 1254
pixels. `generate_icons.py` derives the whole set into `assets/`: the sized PNGs,
the canonical 256, a multi-size Windows `.ico`, a macOS `.icns`, the six tray
marks and the donate mark. Nothing is ever upscaled: a master smaller than a
wanted size is reported rather than stretched. The donate mark does not go
through the squaring path the icon takes; it is cropped to its artwork and
scaled by height alone.

## Files

```
VERSION
plainsight.png
generate_icons.py  stamp_version.py
buildexe.py  buildinstaller.py  build_flatpak.sh  clean_flatpak.sh  builddmg.py
build_utils.py  dmg_icon.py
LICENSE  LICENSE-GPL-3.0.txt  LICENSE-LGPL-3.0.txt  INSTALLER_LICENSE
README.md  ARCHITECTURE.md  DESIGN-PLAN.md  TECH_DEBT.md
docs/              the GitHub Pages site
installer/         the setup program, a second application in the same tree
plainsight/
  __main__.py      the composition root
  version.py
  domain/          document.py  library.py  parsing.py  settings.py
                   passage.py
  application/     ports.py  services.py  defaults.py  update.py
  infrastructure/  document_repository.py  document_reader.py  word_reader.py
                   pdf_reader.py  settings_store.py  desktop.py
                   renderer.py  resources.py  platform.py
                   update_source.py
  ui/              main_window.py  top_tray.py  bottom_tray.py  library_tree.py
                   document_view.py  reading_pane.py  auto_scroller.py
                   keyboard_nav.py  theme.py  widgets.py  update_check.py
                   about_dialog.py  licence_dialog.py  dialogs.py
tests/             mirrors the source tree, plus tests/structural/
```

## Quality gates

- A coverage floor of 100% over `domain` plus `application`, the layers reachable
  with no filesystem, no Qt and no editor. Infrastructure and UI carry real tests
  (a tmpdir for the repository, an offscreen `QApplication` for the widgets) but
  sit outside the floor rather than dragging it to a number that means nothing.
- `black --check`, `flake8` and `ruff check` as standing steps, read by exit code.
- Structural tests: layer direction, domain purity, the 400-line cap with its 381
  to 399 danger band, the composition-root whitelist, no module-level singletons,
  the no-write invariant of 13.1, the focus chain walk and QSS scan from
  `noborderfocus`, ring order against drawn order, the donate address asserted
  literally, plus the rule that every kind the application reads has a reader
  able to read it.
- Every guard proved to bite by planting a violation and reading the exit code.

## Versioning and licensing

`VERSION` at the repository root is the single source of truth. The runtime reads
it and the GitHub Pages site is stamped from it by `stamp_version.py`, which the
three Python delivery scripts call before they build. Its scope is the site and
nothing else, because no document outside the site carries a version at all. No
version literal lives anywhere but `VERSION`.

The licence split is three files: `LICENSE` carrying the overview and the
directory to licence map, `LICENSE-GPL-3.0.txt` and `LICENSE-LGPL-3.0.txt`. The
map reads: `plainsight/ui` under LGPL-3.0; domain, application, infrastructure,
the entry point and the build scripts under GPL-3.0.

## Delivery

Windows through `buildexe.py` plus `buildinstaller.py` with a bespoke themed
installer, Linux through `build_flatpak.sh` and `clean_flatpak.sh`, macOS through
`builddmg.py`.
