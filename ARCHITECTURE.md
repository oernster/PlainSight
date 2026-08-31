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
| Nothing is constructed at import time | `tests/structural/test_composition_root.py::test_nothing_is_constructed_at_import_time` |
| No container class carries a ring rule | `tests/ui/test_focus_rings.py::test_no_container_class_carries_a_ring_rule` |
| The item view takes no ring in any state | `tests/ui/test_focus_rings.py::test_the_item_view_takes_no_hover_ring` |
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
`EditorLauncher`, `ExternalOpener`, `PathProbe`, `PlatformPaths` and
`MarkdownRenderer`.

`defaults` holds the one rule for where skills live when the user has not said
otherwise. The home directory is injected through `PlatformPaths`, which is what
makes the per-operating-system default testable with no operating system.

`SkillLibraryService` is frozen and holds only its injected dependencies. It
answers questions rather than holding answers: `can_open_in_editor` is the enable
predicate for the view in editor control, so the user interface asks rather than
works it out. That predicate needs three things to be true at once: a skill is
selected, an editor was chosen and that editor is still where it was.

### Infrastructure

- `skill_repository`: applies the discovery rules of design plan section 1.
- `settings_store`: versioned JSON, written atomically through a temporary file
  and a replace, so a process that dies halfway leaves the previous settings
  intact.
- `platform`: the home directory and the path probe.
- `markdown_renderer`: rendering through the `markdown` package.
- `resources`: finds the bundled assets and the `VERSION` file across
  development, PyInstaller, Nuitka and a flatpak.

### User interface

Two trays around a split body, exactly as design plan part 2 describes.

- `theme`: one `Palette` and the stylesheet built from it. The ring model has
  three states and no more: nothing at rest, green while hovered or focused and
  enabled, permanent red while disabled. The accent is never a ring.
- `keyboard_nav`: one `KeyboardNavigator` installed as an application event
  filter, driving a ring recomputed live on every move. `NeutralStart` is the
  zero-size sink that absorbs the window's first focus.
- `auto_scroller`: the reading cycle, one per surface, with the constants on the
  class rather than per dialog. A surface beneath a modal is frozen rather than
  suspended; `suspend` is itself gated on the surface being active, so a modal's
  own reset cannot be read as a reader taking hold.
- `top_tray` and `bottom_tray`: each declares `ring_stops()` left to right as
  drawn, so the ring's order is never inferred from a layout walk.
- `skill_list`: one stop, walked with Up and Down, with internal cell tab
  walking turned off so Tab leaves in a single press.
- `skill_view`: the reading pane, a stop only while it overflows.
- `about_dialog`, `licence_dialog`, `widgets`: the dialogs and the pieces they
  share, all on the `FirstStopDialog` base.

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

The read-only invariant of design plan 13.1 is about the application, not the
setup program: an installer writes files by definition. What it never touches
is a skills root; it writes only under `%LOCALAPPDATA%\Programs` and `HKCU`.

## Quality enforcement

The coverage floor is 100% over `domain` plus `application`, the layers reachable
with no filesystem, no Qt and no editor. Infrastructure carries real tests
against a temporary directory but sits outside the floor rather than dragging it
to a number that would mean nothing. `black --check`, `flake8`, `ruff check` and
the pytest gate are all read by exit code.
