# PlainSight

Documents you keep on your own machine end up invisible. They sit in folders
you rarely open; they accumulate quietly, some written months ago, most long
out of mind. You cannot review what you cannot see.

PlainSight makes a folder of documents visible. It walks the folders you point
it at, shows them as the tree they are on disk and renders the one you pick.
Nothing is chosen for you: the pane stays empty until you select something.

It reads nothing at all until you choose a folder. The chooser opens on your
Claude skills folder, which is where this began and is still what most people
point it at, so the common case is one click; take that and the plugins tree
beside it comes too, as a second root. Point it at your notes, your project
documentation or anything else and it reads that the same way.

Nothing is changed by looking. It never writes to a document; editing is handed
to the editor you choose.

## Who it is for

Anyone with a folder of documents they would rather read than grep: Markdown,
text, HTML, Word or PDF. If you keep Claude skills, it answers the three
questions those raise: which are actually on this machine, what one you wrote
three months ago still says, what arrived with a plugin you installed once. If
you keep notes or documentation instead, it reads those with no configuration
at all.

## What it is not

It is not a text editor and it never writes to a document. Editing is handed to
an editor you choose, which is enforced by a structural test rather than left
to discipline.

It is not a search tool and it indexes nothing. It reads the folder when you
open it and again whenever the window comes back to the front.

It makes exactly one network request of its own, never any other: it
asks GitHub whether a newer release of PlainSight has been published. That
happens a few seconds after the window opens, once a day while it stays open
and whenever you ask for it from the Help menu. Nothing about you goes with the
question and there is no telemetry anywhere in it.

Everything else it opens, it opens by handing an address to your desktop for
your browser to fetch, in three places: the donate button, a link you click
inside a document you are reading, then the Download button on an update
prompt. Nothing is fetched or sent without that click.

## Capabilities

- Reads Markdown (`.md`), plain text (`.txt`), HTML (`.html`, `.htm`), Word
  (`.docx`) and PDF (`.pdf`). Markdown is rendered; text is shown exactly as it
  was typed, so its own line breaks survive; HTML is shown as the page it
  already is; a Word document is turned into Markdown as it is read, so it
  reads like the rest.
- Reads a PDF back into the document its page was laid out to be, with its
  pages marked. A PDF holds no headings, no paragraphs and no lists; it holds
  glyphs, each with a place, a size and a face. Ask it for the words alone and a
  CV arrives as a wall of monospace with every heading, every bold phrase and
  every bullet gone. So the sizes and the faces are read the way your eye reads
  them: a line set larger than the body is a heading, a line in bold is
  emphasised, a line opening with a bullet is an item; lines of body text
  running on are one paragraph.
- Is still plain about what that is. It is a reading of the page rather than
  anything the file says, because the file does not say: no fonts, no rules and
  no pictures come across, while a form's grid becomes reading order, since a
  document read back as prose is prose. Where a PDF is a scan, which is a
  picture of a page rather than the words on it, no text can be taken at all
  and it says so rather than showing you nothing. A PDF that is password
  protected says that instead, on its row in the tree before you open it.
- Opens a folder of them without reading them. What a listing costs is opening
  each file, never extracting it: measured over forty PDFs of twelve pages,
  listing took 7ms where extracting them all would have taken 515ms. The text
  is fetched for the one document you pick.
- Runs nothing a document carries. A page's scripts are dropped rather than
  executed, so a document you were sent cannot act on your machine. Anything
  needing a script runtime, htmx among it, is inert here and shows as the
  plain text around it.
- Fetches nothing on a document's behalf. A picture stored beside the document
  is shown; one held at a web address is not fetched and not shown, because the
  reading surface has no way to reach the network. That is not a setting to
  turn on: there is no network in it at all.
- Shows the folders as a tree, each one opening and closing on its own arrow,
  with a count of what it holds so a shut branch says whether it is worth
  opening.
- Reads nothing until you point it at a folder. The chooser opens on your
  Claude skills folder; take that one and the plugins tree beside it comes
  too, as a second root. Any other folder is read on its own, with nothing
  beside it touched.
- Opens a single document too, from the button beside the folder one. That
  reads the one file and lists no directory around it, so whatever sits
  beside it on disk stays unread.
- Renders the document you select, with whatever it declares in its
  frontmatter. Nothing is selected until you select it.
- Holds reflowed text to a readable column, so a wide window buys margins
  rather than longer lines; text that arrived with its own layout, a licence
  for instance, is left exactly as it came.
- Reads itself down the page gently; hands control back the moment you scroll.
- Light and dark, switched from the tray and remembered between runs.
- Three text sizes, stepped by one button in the tray and remembered too.
- Keeps your place when either changes: you stay on the words you were reading
  rather than being thrown back to the top.
- Remembers which folders you left open, so a run opens as the last one closed.
- Full keyboard navigation.
- Opens the selected document in your chosen editor.
- Tells you when a newer release is out, from the Help menu or on its own; skip
  a release and it is never mentioned again.

## Stack

| Concern | Choice |
|---|---|
| Language | Python 3.11 or newer |
| User interface | PySide6 |
| Rendering | markdown |
| Word documents | python-docx |
| PDFs | pypdf |
| Settings | versioned JSON, written atomically |

## Install and run

```
python -m pip install -r requirements.txt
python -m plainsight
```

## Build

The delivery tools are in `requirements-dev.txt`, not `requirements.txt`: they
build the product and the product imports neither of them.

```
python -m pip install -r requirements-dev.txt
```

| Platform | Command | Output |
|---|---|---|
| Windows, the application | `python buildexe.py` | `installer/payload/PlainSight/` |
| Windows, the setup program | `python buildinstaller.py` | `dist-installer/PlainSightSetup.exe` |
| Linux | `./build_flatpak.sh` | `plainsight.flatpak` |
| macOS | `python builddmg.py` | `PlainSight.dmg` |

The icons all derive from one master: `python generate_icons.py` reads
`plainsight.png` at the repository root and writes the whole set into
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

The gate is 100% branch coverage over the domain and application layers, read by
exit code rather than by the last line of output. Those are the layers a machine
can exercise with no filesystem and no toolkit, so anything short of complete
there is a gap nobody chose.

The formatters and linters are separate commands, not assertions inside the
suite. Run all four:

```
python -m pytest
python -m black --check .
python -m flake8 .
python -m ruff check .
```

## Supporting the project

PlainSight is free and stays free. There is no paid tier, no licence key and
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
bundle and the macOS disk image. `ARCHITECTURE.md` holds the invariants and the
design; `TECH_DEBT.md` holds what is still open.
