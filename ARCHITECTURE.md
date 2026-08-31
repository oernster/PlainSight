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

Not yet built. Its design is in `DESIGN-PLAN.md` part 2: two trays, a list and a
rendered pane, one `AutoScroller`, one `KeyboardNavigator` driving the explicit
ring, plus the dialogs.

## Quality enforcement

The coverage floor is 100% over `domain` plus `application`, the layers reachable
with no filesystem, no Qt and no editor. Infrastructure carries real tests
against a temporary directory but sits outside the floor rather than dragging it
to a number that would mean nothing. `black --check`, `flake8`, `ruff check` and
the pytest gate are all read by exit code.
