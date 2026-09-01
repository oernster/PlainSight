# Skills Viewer

Your skills are invisible. They sit in directories you rarely open; Claude
reads them without ever showing them to you; they accumulate quietly, some
written months ago, some arrived with a plugin, most long out of mind. You
cannot review what you cannot see.

Skills Viewer makes that set visible. It finds every skill on your machine,
puts the whole lot in one list and renders the one you pick, so the
instructions you have been giving Claude stop being something you have to take
on trust. Skills you wrote and skills that came with a plugin are separated, so
you can see which is which.

Nothing is changed by looking. It never writes to a skill; editing is handed to
the editor you choose.

## Who it is for

Anyone who keeps a set of Claude skills and has lost track of what is in them.
If you have ever wondered which skills are actually on this machine, what a
skill you wrote three months ago still says, what arrived with a plugin you
installed once, this is the answer to all three. It is designed for Claude AI by
Anthropic and for no other AI. It is not affiliated with Anthropic and is not
endorsed by them.

## What it is not

It is not a text editor and it never writes to a skill. Editing is handed to an
editor you choose, which is enforced by a structural test rather than left to
discipline.

It makes exactly one network request of its own, never any other: it
asks GitHub whether a newer release of Skills Viewer has been published. That
happens a few seconds after the window opens, once a day while it stays open
and whenever you ask for it from the Help menu. Nothing about you goes with the
question and there is no telemetry anywhere in it.

Everything else it opens, it opens by handing an address to your desktop for
your browser to fetch, in three places: the donate button, a link you click
inside a skill you are reading, then the Download button on an update prompt.
Nothing is fetched or sent without that click.

## Capabilities

- Finds skills at the default location for your operating system; browse to any
  other folder instead.
- Lists every skill and renders the selected one, with its declared fields and
  the files that travel with it.
- Holds the text to a readable column, so a wide window buys margins rather
  than longer lines; text that arrived hard wrapped is left exactly as it came.
- Reads itself down the page gently; hands control back the moment you scroll.
- Light and dark, switched from the tray and remembered between runs.
- Three text sizes, stepped by one button in the tray and remembered too.
- Keeps your place when either changes: you stay on the words you were reading
  rather than being thrown back to the top.
- Full keyboard navigation.
- Opens the selected skill in your chosen editor.
- Tells you when a newer release is out, from the Help menu or on its own; skip
  a release and it is never mentioned again.

## Stack

| Concern | Choice |
|---|---|
| Language | Python 3.11 or newer |
| User interface | PySide6 |
| Rendering | markdown |
| Settings | versioned JSON, written atomically |

## Install and run

```
python -m pip install -r requirements.txt
python -m skillsviewer
```

## Build

The delivery tools are in `requirements-dev.txt`, not `requirements.txt`: they
build the product and the product imports neither of them.

```
python -m pip install -r requirements-dev.txt
```

| Platform | Command | Output |
|---|---|---|
| Windows, the application | `python buildexe.py` | `installer/payload/Skills Viewer/` |
| Windows, the setup program | `python buildinstaller.py` | `dist-installer/SkillsViewerSetup.exe` |
| Linux | `./build_flatpak.sh` | `skillsviewer.flatpak` |
| macOS | `python builddmg.py` | `SkillsViewer.dmg` |

The icons all derive from one master: `python generate_icons.py` reads
`skillsviewer.png` at the repository root and writes the whole set into
`assets/`, along with the tray marks and the donate mark.

`python stamp_version.py` writes the version from `VERSION` into the delimited
tokens of the GitHub Pages site under `docs/`, which carries one on each of its
four pages. It is idempotent, so running it on a current tree changes nothing.
The three Python delivery scripts call it before they build, so a packaged
release cannot ship a site that reads behind the version; `build_flatpak.sh`
does not, so run it by hand when a Linux build is the only one made.

The setup program installs into your own account only. It writes under
`%LOCALAPPDATA%\Programs` and `HKCU`, so Windows never asks for an
administrator; it removes cleanly from the Apps list.

## Test

```
python -m pytest
```

The gate is 100% coverage over the domain and application layers, read by exit
code rather than by the last line of output.

The formatters and linters are separate commands, not assertions inside the
suite. Run all four:

```
python -m pytest
python -m black --check .
python -m flake8 .
python -m ruff check .
```

## Supporting the project

Skills Viewer is free and stays free. There is no paid tier, no licence key and
no feature held back behind a donation.

The donate button sits at the left of the bottom tray. Pressing it hands one
address to your desktop for your browser to open; the application fetches
nothing itself there, so the button adds nothing to what is said above about
the network.

## Licence

The user interface is under LGPL-3.0. The domain, application, infrastructure,
entry point, the setup program and the build scripts are under GPL-3.0. Both
texts are in the repository and both are reachable from the buttons in the
bottom tray. See `LICENSE` for the map.

## Status

Every layer is built and gated; all four delivery paths have produced an
artefact: the first release carries the Windows setup program, the flatpak
bundle and the macOS disk image. `DESIGN-PLAN.md` holds the requirements and
the design; `TECH_DEBT.md` holds what is still open.
