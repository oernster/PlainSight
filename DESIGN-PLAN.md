# Skills Viewer: plan and design

## What it does

Displays the skills used by Claude. It reads a directory of Claude skills, lists
them, renders the selected one for reading and hands editing to an editor the
user chooses. It is not a text editor and it never writes to a skill.

## Identity

- GitHub repository: `SkillsViewer`
- Application name: Skills Viewer
- Author: Oliver Ernster
- Tech stack: Python plus PySide6
- UI licence: LGPL-3.0
- Model licence: GPL-3.0

## Scope, stated once

For Claude AI by Anthropic and for no other AI. Not affiliated with Anthropic and
not endorsed by them; the About dialog says both.

---

# Part 1: requirements

## 1. What a skill is

1.1 A skill is a **directory containing `SKILL.md`**. That file is the skill's
document; the directory name is its fallback identity.

1.2 A directory with no `SKILL.md` is **not a skill** and is not listed. Measured
on the author's own tree, `first_finds` and `references` are exactly this case:
directories of markdown with no `SKILL.md` between them.

1.3 A loose `SKILL.md` at the root of the tree **is** a skill. Its identity comes
from its frontmatter `name`, since it has no directory of its own.

1.4 Files beside `SKILL.md` inside a skill directory are that skill's
**companions** (`packaging.md`, `resume-path.md`, `sweep.py`, `audit.py` are all
real examples). They are recorded on the skill and named in the view; they are not
listed as skills in their own right.

1.5 Ignored on sight: any directory whose name begins with `.` and any named
`__pycache__`. Both are present in the author's tree (`.ruff_cache`,
`__pycache__`).

1.6 A skill's display name is its frontmatter `name` where present, else its
directory name. Its `description` frontmatter, where present, is the list row's
tooltip.

## 2. Where skills come from

2.1 The default root per operating system, all resolving to the same place:

| OS | Default root |
|---|---|
| Windows | `%USERPROFILE%\.claude\skills` |
| macOS | `~/.claude/skills` |
| Linux | `~/.claude/skills` |

2.2 A browse button on the far left of the top tray lets the user choose a
different folder. The chosen root persists between runs.

2.3 A root that does not exist opens with an empty list and a message inviting
the browse button; so does a root that holds no skills. Neither is an error and
neither gets a dialog.

2.4 **Plugin skills are read as well**, from the `plugins` tree that sits beside
the chosen skills folder under the same `.claude` directory. The scanner takes a
root and knows nothing about which root it is, so this was added by composition
rather than by rewrite, exactly as this section originally said a later version
would. Every `SKILL.md` anywhere beneath that tree is a skill, read by the same
rules and named for the plugin it arrived with. The measured layout buries one
four levels deep; that shape belongs to the tool, so a depth rule outlives a
change to it where a path template does not.

2.5 **Skills are gathered by where they came from**, under a heading each, with
an arrow that opens and closes the group. The axis is origin rather than
authorship, because authorship is written down nowhere and cannot be read off a
file. That has one honest consequence worth stating: a skill somebody else wrote
that sits in the user's own skills folder is listed among his. Where everything
came from one place the headings are left out and the tree reads as a flat list.

2.6 **Still out of scope:** project-scoped skills under a repository's
`.claude/skills`, plus any skill that is not a file under the chosen tree.
Several that a session offers are supplied by the tool rather than stored on
disk, so nothing here can see them and nothing here pretends to.

## 3. Displaying a skill

3.1 Skills are listed one per row, sorted case-insensitively by display name.
Exactly one skill is displayed at a time.

3.2 Layout is a list on the left and the rendered skill on the right. Sequential
presentation alone was rejected: reaching the eleventh skill would mean stepping
through ten.

3.3 The markdown is **rendered**, not shown as source, in a readable proportional
font with monospace for fenced code. Rendering brings one new runtime dependency
(`markdown`, BSD), credited in About.

3.4 The frontmatter block is stripped before rendering and surfaced as a compact
header above the body: name, description, then any other fields the skill
declares.

3.5 Companions are named beneath that header, so a skill that is more than one
file says so.

3.6 Selecting a different skill replaces the pane's content and returns the
auto-scroll cycle to its start hold rather than continuing mid-descent.

## 4. Auto-scroll (the `scroll` skill)

4.1 Applied to the rendered skill pane, the About dialog, the UI licence dialog
and the model licence dialog. All four are read through rather than acted on,
which is the boundary that skill draws.

4.2 **Not** applied to the skill list, which is a surface to act on.

4.3 One set of constants on the scroller class, never per surface: 40ms tick,
5000ms start hold, 1px per two ticks descending, 5000ms bottom hold, 15px per tick
rewind, 2000ms top hold, 2500ms resume after manual input.

4.4 The overflow guard means attaching it to a short skill is free and correct.

## 5. Help and About

5.0 An appearance toggle immediately left of the help button. It wears the
application's own light and dark artwork and shows the appearance it would move
**to**, so the sun appears while you are in the dark. Repainting, re-facing the
toggle and re-rendering the open skill all happen in one call, so it can never
be left showing the mode just departed. The choice persists between runs; each
palette names its own ring and danger tokens rather than sharing one pair.

5.1 A help and about button on the far right of the top tray.

5.2 About shows the application icon, the name, the version, "Oliver Ernster",
the copyright with its symbol, the dual licence line and credit where credit is
due: every real dependency named with its licence.

5.3 About states plainly that Skills Viewer is designed for Claude AI by Anthropic
and for no other AI. It states just as plainly that it is not affiliated with or
endorsed by Anthropic.

## 6. Choosing an editor

6.1 A choose editor button in the top tray, immediately right of the browse
button.

6.2 It opens a file chooser for the editor executable. The choice persists between
runs, recorded as a path plus a display name.

## 7. Viewing in the editor

7.1 A view in editor button in the top tray, immediately right of the choose
editor button.

7.2 It launches the chosen editor with the selected skill's `SKILL.md` as the file
to edit. This application is not a text editor replacement.

7.3 It is **disabled by default**. The enable predicate, stated so the keyboard
ring can honour it: enabled when a skill is selected **and** an editor is chosen
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
4. appearance toggle
5. help and about
6. the skill list (one stop; Up and Down walk the rows)
7. the rendered pane, **only while it overflows**
8. donate
9. UI licence
10. model licence

then wrapping back to the browse button.

8.3 Both trays declare their own `ring_stops()` left to right as drawn, so the
collector never infers order from a layout walk.

8.4 The main window starts neutral. Every dialog opens already focused on its
first enabled, visible, focusable control.

8.5 Ring colours: no ring at rest, green while hovered or focused and enabled,
permanent red while disabled. The brand accent is never a ring.

8.6 No container is a stop and no container paints a ring. The skill list is an
item view, so it rings in **no** state; its current row is the indicator. The
rendered pane is a scrolling region, so it rings on focus only and never on hover.

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
scaled by height. The address is Skills Viewer's own, generated for this
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
edit a skill and comes back sees current content; a skill added or removed while
away appears or disappears. No file watcher, no polling thread.

12.2 A `SKILL.md` that cannot be decoded is still listed; so is one whose
frontmatter is malformed. The failure is shown in the pane rather than raised as
a dialog: the user did not cause it and cannot fix it from here.

## 13. Read only, as an invariant

13.1 The application never writes to any path beneath the skills root. Editing is
exclusively the external editor's job.

13.2 This is enforced by a structural test rather than by convention, in the same
spirit as the no-network test in `postal-gambit`.

## 14. Telling the user a newer release exists

14.1 The help control in the top tray drops a menu of two: About Skills Viewer,
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
trays, the tree and the skill being read together. It is remembered between
runs beside the appearance.

15.5 A change of colour or of size redraws the page but does not move the
reader: they are put back on the words they were on. The place is an offset
into the text rather than a scroll position, since at another size the same
point down the page is different words. It is taken before the stylesheet
changes, because applying it has already reflowed the page.

---

# Part 2: design

## Architecture invariant

`UI -> Application -> Domain <- Infrastructure`, enforced by structural tests.

## Domain (stdlib only, no I/O, no clock)

Frozen dataclasses with `slots=True`, `tuple[...]` over `list`.

- `SkillDocument`: the parse result of a `SKILL.md`, holding `frontmatter` and
  `body`. Splitting the two is pure string work, so it lives here.
- `Skill`: display name, description, directory, document path, companions and
  body. Validates in `__post_init__`.
- `SkillCatalogue`: an ordered `tuple[Skill, ...]` with `by_name()` and the sort
  rule.
- `EditorChoice`: path plus display name, validating that the path is non-empty.

## Application (domain plus stdlib only)

Ports, all Protocols:

- `SkillRepository`: `list_skills(root) -> SkillCatalogue`
- `SettingsStore`: `load() -> Settings`, `save(settings)`
- `EditorLauncher`: `launch(editor, target) -> bool`
- `ExternalOpener`: `open(address) -> bool`
- `MarkdownRenderer`: `render(body) -> str`

Services:

- `SkillLibraryService`, frozen, holding its injected dependencies. It owns which
  root is active, which skill is current and whether the editor can be launched.
  The enable predicate of 7.3 lives here, so the UI asks a question rather than
  computing one.
- `default_skills_root(paths)`, a pure function over an injected paths provider,
  so the per-OS defaults are unit-testable with no operating system involved.

## Infrastructure

`FileSystemSkillRepository` (the scan and the ignore rules of section 1),
`JsonSettingsStore` (atomic write by temp file plus `os.replace`, versioned
`{"version": 1, ...}`), `DesktopEditorLauncher` (`QProcess.startDetached`),
`QtExternalOpener` (`QDesktopServices.openUrl`), `PythonMarkdownRenderer`, plus
`resources.py` carrying `data_path_resolver` and `icon_resolver` so assets resolve
under development, PyInstaller, Nuitka and Flatpak alike.

## UI

```
top tray:    [folder] [choose editor] [view in editor] .......... [help/about]
body:        skill list (left)            |  rendered skill (right)
bottom tray: [donate] [UI licence] [model licence] ..............
```

One `AutoScroller` class carrying the canon constants. One `KeyboardNavigator`
installed as an application event filter, driving the ring of section 8. A theme
module holding semantic tokens, with `ring` and `danger` named per theme so the
three-state colour model holds by construction.

Dialogs: `AboutDialog`, plus one `LicenceDialog(title, path, parent)` reused by
both licence buttons, each derived from the first-stop dialog base.

## Assets

The master is `skillsviewer.png` at the repository root, square RGBA at 1254
pixels. `generate_icons.py` derives the whole set into `assets/`: the sized PNGs,
the canonical 256, a multi-size Windows `.ico`, a macOS `.icns`, the six tray
marks and the donate mark. Nothing is ever upscaled: a master smaller than a
wanted size is reported rather than stretched. The donate mark does not go
through the squaring path the icon takes; it is cropped to its artwork and
scaled by height alone.

## Files

```
VERSION
skillsviewer.png
generate_icons.py  stamp_version.py
buildexe.py  buildinstaller.py  build_flatpak.sh  clean_flatpak.sh  builddmg.py
LICENSE  LICENSE-GPL-3.0.txt  LICENSE-LGPL-3.0.txt  INSTALLER_LICENSE
README.md  ARCHITECTURE.md  TECH_DEBT.md
skillsviewer/
  domain/          skill.py  skill_document.py  catalogue.py  editor_choice.py
  application/     ports.py  services.py  defaults.py
  infrastructure/  skill_repository.py  settings_store.py  editor_launcher.py
                   markdown_renderer.py  resources.py
  ui/              main_window.py  top_tray.py  bottom_tray.py  skill_tree.py
                   skill_view.py  reading_pane.py  auto_scroller.py
                   keyboard_nav.py  theme.py
                   about_dialog.py  licence_dialog.py  links.py
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
  literally.
- Every guard proved to bite by planting a violation and reading the exit code.

## Versioning and licensing

`VERSION` at the repository root is the single source of truth. The runtime reads
it; markdown and any site content are stamped from it by `stamp_version.py`, which
the build scripts call. No version literal lives anywhere else.

The licence split is three files: `LICENSE` carrying the overview and the
directory to licence map, `LICENSE-GPL-3.0.txt` and `LICENSE-LGPL-3.0.txt`. The
map reads: `skillsviewer/ui` under LGPL-3.0; domain, application, infrastructure,
the entry point and the build scripts under GPL-3.0.

## Delivery

Windows through `buildexe.py` plus `buildinstaller.py` with a bespoke themed
installer, Linux through `build_flatpak.sh` and `clean_flatpak.sh`, macOS through
`builddmg.py`.
