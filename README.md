# Skills Viewer

A reader for the skills used by Claude AI. It finds the skills on your machine,
lists them, renders the one you pick and hands editing to the editor you choose.

## Who it is for

Anyone who keeps a set of Claude skills and wants to read them without opening a
file manager first. It is designed for Claude AI by Anthropic and for no other
AI. It is not affiliated with Anthropic and is not endorsed by them.

## What it is not

It is not a text editor and it never writes to a skill. Editing is handed to an
editor you choose, which is enforced by a structural test rather than left to
discipline.

It makes no network request of its own: there is no HTTP client, no socket and
no telemetry anywhere in it. What it does do is hand an address to your desktop
for your browser to open, in exactly two places: the donation button, then a
link you click inside a skill you are reading. Nothing is fetched or sent without
that click.

## Capabilities

- Finds skills at the default location for your operating system; browse to any
  other folder instead.
- Lists every skill and renders the selected one, with its declared fields and
  the files that travel with it.
- Reads itself down the page gently; hands control back the moment you scroll.
- Full keyboard navigation.
- Opens the selected skill in your chosen editor.

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
| macOS | `python builddmg.py` | `dist/skillsviewer-macos-arm64.dmg` |

The icons all derive from one master: `python generate_icons.py` reads
`skillsviewer.png` at the repository root and writes the whole set into
`assets/`, along with the tray marks and the donate mark.

`python stamp_version.py` writes the version from `VERSION` into the delimited
tokens of a GitHub Pages site. There is no site yet, so it currently reports
that nothing needed stamping; all three build scripts call it first regardless,
so a site can never ship behind the version.

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

## Licence

The user interface is under LGPL-3.0. The domain, application, infrastructure,
entry point, the setup program and the build scripts are under GPL-3.0. Both
texts are in the repository and both are reachable from the buttons in the
bottom tray. See `LICENSE` for the map.

## Status

Every layer is built and gated, with all four delivery paths written. The
Windows pair has been run end to end and the built application starts; the Linux
and macOS scripts have not been run, since neither platform is to hand; the
setup program has not been installed from either. `DESIGN-PLAN.md` holds the
requirements and the design; `TECH_DEBT.md` holds what is still open.
