# Decisions and trade-offs

The deliberate choices PlainSight rests on: what was chosen, what was given up
for it and why. Each entry is the decision as the product makes it today.
The detail behind each one, with the tests that hold it, lives in
[ARCHITECTURE.md](ARCHITECTURE.md) and the specifications
([DESIGN-PLAN.md](DESIGN-PLAN.md), [RELEASE-IMPORT.md](RELEASE-IMPORT.md));
[TECH_DEBT.md](TECH_DEBT.md) holds what is still open and what only looks like
debt.

## The product as a whole

### A reader, never a writer

PlainSight never writes to a document it is pointed at. Editing is handed to
an editor the reader chooses. The only things it writes are its own: its
settings and any release notes the reader asks it to import. A structural
test grants each module the writes it needs by name and fails on any other
write it can see. The Flatpak is granted the home folder read only, with only
the application's own folder writable.

- **Rather than:** a viewer with editing built in; a check that listed a few
  writing calls by name, which the audit found blind to most ways of writing.
- **Gains:** looking at a folder cannot change it; a new way of writing in a
  new place fails the test rather than slipping past it.
- **Costs:** every correction means a trip to another program. The test reads
  names, not types, so a string's `replace` reads as a write; it cannot see a
  library writing on the application's behalf. Under the Flatpak an editor
  started from inside the sandbox could not save to the home folder either.

### Any folder of documents, not one kind of file

A document is any file of a kind PlainSight reads: Markdown, plain text, HTML,
Word and PDF. It began as a viewer for Claude skills, tied to one file name.

- **Rather than:** discovery tied to skill folders, which listed nothing in a
  folder of ordinary notes.
- **Gains:** notes, project documentation and skills are read the same way
  with no configuration.
- **Costs:** a reader to maintain for every kind where there was one.

### What PlainSight deliberately is not

It is not an editor, a search tool or a GitHub client. It indexes nothing; it
reads the folder when it is opened and again when the window comes back to
the front.

- **Rather than:** an all-purpose document workbench.
- **Gains:** a small surface held to a high bar.
- **Costs:** searching across documents needs another tool.

### Specification before code

The design is written as numbered requirements before it is built. The
release notes import has its own specification in which every requirement
names the test that verifies it, with a list of what is deliberately out of
scope.

- **Rather than:** building first and describing afterwards.
- **Gains:** a ruled-out idea stays ruled out; a claim in the docs is one a
  test holds.
- **Costs:** keeping the specifications true is work of its own; documentation
  passes keep finding claims that have drifted.

## Reading only what was asked

### Nothing is read until a folder is chosen

There is no default folder and no first-run scan. A fresh install opens on an
empty tree and an invitation, having listed no directory at all. The folder
chooser opens on the last folder taken, else the home directory. Where it
opens is kept apart from what is read: a folder offered in a dialog has not
been read.

- **Rather than:** opening on the Claude skills folder, as it once did;
  starting the chooser in a documents folder, which one operating system gates
  by name.
- **Gains:** reading somebody's files is theirs to authorise; the starting
  place raises no permission prompt on any of the three operating systems.
- **Costs:** a first run shows nothing until the reader acts.

### A neighbouring folder only where it is implied

The plugins tree beside a Claude skills folder is read as a second root only
when the chosen folder plainly is one. Any other folder is read on its own.

- **Rather than:** reading a sibling plugins folder beside whatever was
  chosen, which once meant choosing a notes folder walked whatever sat next
  door.
- **Gains:** exactly one directory is read unless the choice plainly means two.
- **Costs:** a plugins tree kept anywhere else is not found.

### One file opened lists no directory

A single document can be opened on its own. Its folder row is named from the
path rather than looked into, so nothing beside it is read. The choice is not
remembered; the next run opens on the chosen folder.

- **Rather than:** opening the file's folder to show it in place.
- **Gains:** one file opened is one file read.
- **Costs:** the documents beside it need the folder chooser.

### Nothing is selected until the reader selects it

There is no fallback to the first row. The pane opens empty, saying so.

- **Rather than:** selecting the first document, which chose one again on
  every return to the window while the pane scrolled through a file nobody
  had opened.
- **Gains:** what is on screen is always what the reader asked for.
- **Costs:** one more click on a first visit.

### Fresh on every return to the window

The library is read again whenever the window is activated. There is no file
watcher and no polling. A listing keeps what each document says about itself
and a fingerprint of its file, never its text. The text is read for the one
document that is opened; a document already on screen and unchanged is not
drawn again.

- **Rather than:** watching the folders for changes; holding every document's
  text in memory; redrawing on every read, which sent the reader back to the
  top whenever they left the window.
- **Gains:** a reader who leaves to edit a document comes back to the current
  text at the place they left; nothing runs in the background; a folder of
  large PDFs lists quickly.
- **Costs:** the listing is paid for on every activation, so it has to stay
  cheap; a document that has gone by the time it is opened has to say so.

### A document that cannot be read is still listed

A locked, damaged or unreadable file keeps its row. The reason is shown in
place of the body; a password-protected PDF says so on its row before it is
opened.

- **Rather than:** a dialog; leaving the file out.
- **Gains:** the reader sees everything that is there and why some of it
  cannot be read.
- **Costs:** the tree can hold rows that open onto an explanation rather than
  a document.

### Somebody else's code and empty files hidden by default

While the tree filter is on, which it is until the reader turns it off,
Python environment and Node package folders are passed over and documents
holding no text are left out, along with any folder left with nothing to
read. Emptiness is judged only from what listing already cost, so a PDF is
never judged. A document opened on its own is never filtered. One button turns
the filter off and on.

- **Rather than:** showing everything; a right-click menu on the tree with the
  filter off by default, which it replaced.
- **Gains:** licence and metadata files from installed packages stay out of
  the tree.
- **Costs:** an empty PDF still shows; a document the reader wanted inside one
  of those folders needs the filter turned off.

## Documents and what they become

### One home for the kinds

Which file names are read, whether a kind declares fields, how its text
reaches the screen and what it is called in front of a reader all live in one
place. A body is laid out for the page, kept exactly as typed or handed over
as the HTML it already is. The reader for each kind is named by hand rather
than derived; a test requires every kind to have one.

- **Rather than:** lists of file types held by each part that cares; a flag
  for how text is shown, which had nowhere to put HTML.
- **Gains:** the chooser, discovery and rendering cannot disagree; a kind
  added without a reader fails a test rather than being read by the wrong one.
- **Costs:** adding a kind touches two places on purpose.

### Plain text is shown exactly as typed

A text file is shown as its own characters and line breaks, never passed
through the Markdown renderer.

- **Rather than:** rendering it as Markdown, which would turn a line of
  hyphens into a heading rule and lose the author's line breaks.
- **Gains:** three hyphens in a text file are three hyphens.
- **Costs:** a text file that happens to be written in Markdown is shown as
  source.

### HTML is shown as the page it is; nothing in it runs

An HTML document is handed to the reading surface untouched. Scripts neither
run nor appear as text; a picture held at a web address is not fetched.

### What a document may reach is decided by PlainSight, not by Qt

Qt's reading surface fetches nothing over the web. Left alone, though, it reads a
picture from a network share (`\\server\share`, `//server/share`,
`file://server/...`), looks for a relatively named one in whatever folder the
application started in and hands any clicked link to whichever program owns
its scheme; a `file:` link replaced the page. All of that was measured. So one
rule, in the domain, decides both. A picture is read from this computer only:
a relative name from the document's own folder, climbing out with `..` while
it stays local; anything naming a host is refused. A link is handed to the
browser only for `https`, `http` and `mailto`; a link within the page scrolls;
every other link does nothing.

The rule is applied twice in the pane, because refusing in the loader alone
was measured not to stop the read: Qt reads a picture again by its own name
once the loader's answer will not decode. Every picture is therefore renamed
to the local file it resolves to (or to nothing) before layout; the loader
answers a refusal with Qt's own missing picture.

- **Rather than:** trusting Qt's defaults; a filter in the loader alone.
- **Gains:** opening a document somebody sent cannot make the machine reach a
  share it names, nor start a protocol handler with a history of abuse.
- **Costs:** a page that needs scripts or remote pictures shows only the text
  around them; `ftp:`, `file:` and every other link does nothing. A drive
  letter mapped to a share reads as local, since its name cannot say otherwise.

### Word documents become HTML, not Markdown

A Word document is converted to HTML as it is read, so the reading pane never
learns where it came from. Headings, paragraphs, lists, tables and emphasis
cross; presentation does not. A table is drawn as a table only when it has
something to tabulate, since Word lays pages out with tables as often as it
tabulates.

- **Rather than:** Markdown, the first answer, where text that means nothing
  in Word became syntax on the way through and guarding against each case had
  no end; drawing every layout table as a table.
- **Gains:** escaping into HTML is total, so nothing an author typed can be
  misread as markup; a Word document reads as the document it looks like.
- **Costs:** fonts, colours and page layout are not carried across; a genuine
  single-row or single-column table is shown as plain blocks.

### A PDF is rebuilt into the document its page was laid out to be

A PDF holds glyphs with places, sizes and faces rather than headings and
paragraphs, so those are read back the way an eye reads them: larger than the
body is a heading, bold is emphasis, a bullet opens an item and running lines
are one paragraph. Every threshold was measured on real files. A page that
cannot be rebuilt falls back to its plain words.

- **Rather than:** the words alone, which turned a real CV into a wall of
  monospace with every heading and bullet gone.
- **Gains:** a PDF reads like the rest; a failure costs the layout rather than
  the page.
- **Costs:** a form's grid becomes reading order. No fonts, rules or pictures
  come across; a scan yields no text at all.

### A reader never takes the application down

The Word and PDF readers catch every failure when opening a file, each catch
carrying its reason. They parse files somebody else chose, through libraries
with no contract about what they raise.

- **Rather than:** catching a list of the failures seen so far.
- **Gains:** a broken file costs its own row, never the session.
- **Costs:** a genuine fault inside a reader is reported as an unreadable file.

### Long text is arranged for reading, never rewritten

An over-long passage is shown in groups of whole sentences with a gap between
them, falling back to the divisions its author did write. A declared field too
long for the header is given its own section after the body. Nothing is
added, removed or reordered; a test takes the breaks out again to prove it.

- **Rather than:** showing walls of text as they arrive; rewriting them.
- **Gains:** the eye has somewhere to rest; the reader lands on the text they
  opened rather than beneath a field.
- **Costs:** the breaks are PlainSight's, not the author's; a long field is
  found at the foot rather than the head.

### The status bar counts the text, not the file

The foot of the window names the kind of document and counts the characters
and lines of the text being read: a Markdown document beneath its declared
fields, a PDF or Word document as what was read out of it. A document that
could not be read names its kind and carries no count.

- **Rather than:** a byte count of the file.
- **Gains:** the figure means the same thing for every kind.
- **Costs:** it says nothing about how large the file itself is.

## The network

### Two requests of its own, never a third

PlainSight asks GitHub whether a newer release of itself exists. It also asks
GitHub for a repository's releases when the reader imports them. It opens no
other connection and carries no telemetry. Both follow a redirect only while it
stays on the host they asked. The donate button, a web or mail link clicked
inside a document and the Download button on an update prompt each hand an
address to the desktop for the browser to fetch.

- **Rather than:** a reader that fetches on a document's behalf; usage
  reporting.
- **Gains:** nothing leaves the machine without the reader's knowledge.
- **Costs:** no usage figures to steer development.

### Update checks: daily, quiet unless there is news

A check runs shortly after the window opens and once a day while it stays
open, with a short time limit and no retries. It asks only for the latest
published release, so a pre-release or draft is never offered. A check nobody
asked for speaks only when there is something to download; one from the Help
menu reports every outcome. A version it cannot read is never treated as
newer. A skipped release is one remembered release.

- **Rather than:** no check at all; one that reports every outcome.
- **Gains:** updates are found without nagging; a malformed tag can never
  raise a prompt; skipping one release still lets the next one through.
- **Costs:** one unprompted request a day.

### No credential compiled in

Both requests go to GitHub without a token or an account.

- **Rather than:** an authenticated client.
- **Gains:** nothing to leak or to configure.
- **Costs:** the release import is held to GitHub's hourly allowance for
  requests made without an account, so it asks for as many releases per
  request as GitHub allows.

### The donation address is pinned literally

The donate address has one home. Structural tests assert it character for
character, assert its scheme and assert it appears exactly once.

- **Rather than:** a check of its shape.
- **Gains:** a transposed character cannot send a supporter to someone else's
  page.
- **Costs:** changing the page means changing the test too.

## Importing release notes

### Release notes become a folder of ordinary Markdown

An import writes one Markdown file per published release beneath the
application's own directory, then opens that folder on the newest release.
Each file is a small header, a rule, then GitHub's notes unchanged. Drafts
are left out and pre-releases marked.

- **Rather than:** a GitHub client inside the reader, with issues, commits,
  tags or downloads.
- **Gains:** the notes are read by everything already built; the folder is
  the reader's to keep.
- **Costs:** the folder is a copy, current only as of the last import.

### Every request before any write; never half a history

All of GitHub's answers are gathered and the whole refresh is planned before
a byte is written. A stop is honoured until writing starts and never after. A
first import is built out of sight and moved into place only when complete; a
refresh replaces each file whole and its record last. Staging left behind by
an import that died is swept once it is old enough that no live import can
still be writing it.

- **Rather than:** writing each release as it arrives; writing into the
  collection directly.
- **Gains:** a failure asking GitHub, where nearly every failure is, leaves
  the disk untouched; a failed first import leaves no collection and a failed
  refresh leaves every file either as it was or as it should be.
- **Costs:** a large history is held in memory until it is written; dead
  staging waits a while before it is cleared.

### The reader's edits and withdrawn releases are kept

A file is known by its release and by a fingerprint of what was last written
to it. A refresh rewrites a file only when it is unedited and GitHub's text
changed. A file the reader edited is kept and reported; a release GitHub no
longer lists keeps its file.

- **Rather than:** overwriting the folder with GitHub's current answer.
- **Gains:** once written, the files are the reader's own.
- **Costs:** edits are never merged with later changes on GitHub.

### A bad answer fails the import

A malformed entry in GitHub's answer fails the whole import rather than being
skipped. An oversized page is refused unread, a next page anywhere but
GitHub's own API is refused and retrieval stops at a fixed number of pages.

- **Rather than:** importing what could be read.
- **Gains:** a history never silently misses a release; a hostile or broken
  answer cannot run away with memory or time.
- **Costs:** one bad entry blocks the rest.

### A folder may declare its order, generically

A collection carries a hidden record naming its documents in order, newest
first by publication date. The tree reads only that list; documents it does
not name follow by name.

- **Rather than:** encoding the order in the file names; GitHub-specific code
  in the tree.
- **Gains:** the tree and the renderer know nothing of GitHub.
- **Costs:** a record somebody edited has to be checked before it is
  believed.

### Imported notes live with the settings and leave with them

Collections sit under the application's own directory in the home folder.
Uninstalling removes that directory, edited notes included.

- **Rather than:** a folder the reader chooses; one that survives removal.
- **Gains:** one place for everything PlainSight writes; an uninstall leaves
  nothing behind.
- **Costs:** notes worth keeping have to be copied out before removal.

## The interface

### The reader keeps their place through a redraw

A change of colour or text size draws the page again without moving the
reader. The new page is built, styled and laid out before it is attached, so
there is no moment at which the position can be lost; where the layout moved
under a new size, the place is followed into the text rather than kept as a
scroll position.

- **Rather than:** setting the text on the live widget and restoring the
  place afterwards, which lost it in a race.
- **Gains:** the reader stays on the words they were reading.
- **Costs:** a more intricate redraw than setting text.

### A readable column that does not pen in code

Prose wraps at a readable line length, so a wide window buys margins rather
than longer lines. The cap is on where a line wraps rather than on how much of
the pane a page may use, so a block of code or a diagram is drawn as one box,
in a face whose box-drawing strokes join up, keeping every pixel the window
has. Text that arrived hard wrapped is left as it came.

- **Rather than:** shrinking the pane to the column, which penned wide diagrams
  into the same narrow strip; the toolkit's own drawing of code, which broke
  it into a ragged staircase of dashed lines.
- **Gains:** prose reads comfortably and diagrams scroll sideways only when
  the window is genuinely too narrow.
- **Costs:** a wide window leaves much of its width as margin.

### The page reads itself

The document pane, the guide, About and both licences scroll gently on their
own and hand control back the moment the reader takes over. One set of
timings serves every surface; a page that fits is left still. A dialog is
destroyed when it closes, so no cycle carries on behind the window.

- **Rather than:** static pages; dialogs kept hidden for reuse, which left
  their reading cycles running.
- **Gains:** long text can be read hands free; nothing runs that the reader
  cannot see.
- **Costs:** a page in motion the reader did not start; a dialog is built
  afresh each time.

### Three text sizes from one button

Three sizes are stepped by one button that wraps back to the start, derived
from one base and one step. The rendered page declares no size of its own, so
a change reaches the trays, the tree and the page together.

- **Rather than:** a continuous scale.
- **Gains:** one button, walkable in a moment; the sizes cannot drift apart.
- **Costs:** no size between the three.

### A cycling button shows where a press leads

The appearance and text size buttons wear the state a press would move to.
The tree filter button is the exception: its picture shows the filter as it
stands while its tooltip offers the press.

- **Rather than:** one rule for every toggle.
- **Gains:** each picture answers the question a reader asks of it.
- **Costs:** two conventions to learn.

### Full keyboard reach, rings only on controls

One explicit ring, declared by each tray in drawn order, reaches every
control; the reading pane joins it only while it overflows. A focus ring
belongs to a control, never to the tree or the page being read.

- **Rather than:** a focus order inferred from the layout; rings on panes.
- **Gains:** the whole application works without a mouse; clicking the text
  never draws a rectangle round the page.
- **Costs:** every new control needs its place in the ring.

### Help lives on the controls, with one short guide

Every control carries a tooltip, shown even while another program has focus.
A help button drops a short menu, the Guide first, then About, then the update
check, with no menu bar. The guide names each tray control with the icon the
tray itself draws, then says what each kind of document becomes on the way to
the pane.

- **Rather than:** a menu bar; screenshots or descriptions of the pictures;
  the toolkit's default of withholding tooltips from an inactive window.
- **Gains:** the tray stays a row of pictures; the guide cannot drift from the
  interface and stays short enough to finish.
- **Costs:** the guide is generated rather than freely laid out.

### Contrast held by test

Light and dark each name their own ring and danger colours. Every pairing
that carries text is held to the WCAG AA ratio by a test, in the application
and the setup program.

- **Rather than:** judging colours by eye, under which several pairings looked
  deliberate and were unreadable.
- **Gains:** a colour that cannot be read fails the suite rather than
  shipping.
- **Costs:** the dark theme needs a selection fill of its own, since one accent
  cannot both read on the panel and carry white.

### Folders open shut and stay as left

The tree remembers which folders the reader opened, by path. A fresh install
opens with every folder shut.

- **Rather than:** remembering which were closed; opening everything.
- **Gains:** a run opens as the last one closed; two folders sharing a name
  are never confused.
- **Costs:** a first visit to a deep tree takes some opening.

## Building and installing

### Nuitka, with unused parts of Qt fenced out

The application, the setup program and the macOS application are compiled
with Nuitka; the Linux flatpak runs the source under its runtime's own Python.
The build fences out the parts of Qt nothing imports. Every Nuitka build
refuses to start on a Nuitka older than the release it is written against.

- **Rather than:** PyInstaller, which bundles an interpreter beside the source;
  collecting Qt whole under it produced a far larger bundle; compiling with
  whichever Nuitka happens to be installed.
- **Gains:** one rule finds the bundled files in development and under a
  compiled build alike; nothing unused can creep in through an indirect
  import; what ships is compiled by a release somebody chose.
- **Costs:** some packages must be named for inclusion by hand, which ties the
  build to how those libraries load; a new Qt feature may need the fence moved;
  an old environment has to upgrade Nuitka before it can build at all.

### Installed for one user, without administrator rights

The Windows setup program writes under the user's own program folder and
registry hive. Removing PlainSight also removes its settings directory,
imported release notes included; documents are never touched.

- **Rather than:** a machine-wide install; leaving settings behind on removal.
- **Gains:** no administrator prompt; installing again starts as a first
  install does rather than reviving a folder chosen months earlier.
- **Costs:** each account installs separately; uninstalling loses the
  remembered choices.

### A setup program of its own

Install, update, downgrade, management and removal are one bespoke program.
It moves between screens rather than greying controls in place, rebuilds its
footer per screen, weights its progress by measured time and ends every path
in a verdict. Every entry in the payload is checked to land inside the install
folder before any is written. When it starts the application it hands that
process the foreground, which the application then takes.

- **Rather than:** a generic installer; a plain show, which opened the window
  behind everything after a fresh install.
- **Gains:** one identity throughout; a crafted archive cannot write half its
  contents before it is caught; the application comes to the front when setup
  finishes.
- **Costs:** the setup program is PlainSight's own to maintain; foreground
  handling cannot be checked offscreen, so it is tested at the mechanism.

### Each platform builds on itself

Windows, macOS and Linux packages are built by their own scripts on their own
platforms. The macOS application and its disk image are signed and
notarised.

- **Rather than:** cross-compiling.
- **Gains:** each package is built by the tools that know that platform.
- **Costs:** a machine of each kind and an Apple developer account; Windows
  is the one built regularly, so the other two can fall behind.

### Dependencies declared, kept apart and credited

The delivery tools sit in the development requirements, since the
application imports none of them. A structural test checks that every package
imported and every tool run as a subprocess is declared; another compares the
About dialog's credits with both requirements files.

- **Rather than:** one requirements file; trusting an import scan, which
  cannot see a tool started as a subprocess; a credit list written once and
  left.
- **Gains:** a fresh checkout can build as well as run; a dependency cannot be
  added without being credited.
- **Costs:** the tests check names; the licence text is still read by a
  person.

### One version, stamped into the site alone

One version file is the single source of truth: the runtime reads it and the
website is stamped from it. No other document carries a version. The settings
file has a format number of its own. The stamper also tags each stylesheet and
script link with a hash of its content.

- **Rather than:** version numbers written into documents; tying the settings
  format to the application version.
- **Gains:** the application version can move without anything being done to
  a user's settings; a browser never pairs a new page with a stale stylesheet.
- **Costs:** the Linux build does not call the stamper, so it is run by hand
  when that is the only build made.

### Icons from one master each

Every icon, nearly every tray mark and the donate mark is generated from a
master image; the three text size marks are drawn by hand. Nothing is
upscaled: a master smaller than a wanted size is reported rather than
stretched. The masters stay out of the bundle, all but the one for the tree
filter's cross, which keeps the name its owner gave it.

- **Rather than:** hand-exported sizes.
- **Gains:** one source per picture; no blurred icon.
- **Costs:** the generator has to be run after any artwork changes.

### Two licences plus a commercial one

The interface is LGPL-3.0; the domain, application, infrastructure, setup
program and build scripts are GPL-3.0. A commercial licence for Oliver's own
code is offered separately.

- **Rather than:** one licence for everything.
- **Gains:** the interface can be reused under the lighter terms Qt itself
  carries.
- **Costs:** two licence files and a map to keep straight.

### Downloads point at the latest release

The website's download buttons follow GitHub's latest-release redirect for
each platform; nothing tells a visitor to build from source.

- **Rather than:** a list of releases to search; clone-and-run instructions.
- **Gains:** the page never needs editing for a new release.
- **Costs:** developers go to the repository instead.

## Engineering

### Layers with one place where they meet

The code is split into domain, application, infrastructure and interface,
each allowed to depend only inward. The domain reads nothing from outside
itself, so paths and moments in time are plain text there. One composition
root builds every implementation; structural tests hold the boundaries and
forbid anything being built at import time.

- **Rather than:** convention alone; path and date objects in the domain,
  which would bring the filesystem and clock with them.
- **Gains:** the rules about documents, releases and updates are tested with
  no disk, network or screen.
- **Costs:** more modules, more explicit wiring and a conversion at every
  boundary.

### Complete coverage where it means something

Branch coverage must be total over the domain and application layers. The
infrastructure, the interface and the setup program carry real tests against
temporary directories and a real offscreen toolkit, outside that figure. The
toolkit suites destroy whatever each test built.

- **Rather than:** one figure over everything, which would mean either a weaker
  number or a list of exclusions.
- **Gains:** anything short of complete in the pure layers is a gap nobody
  chose.
- **Costs:** device, file and screen code relies on targeted tests.

### Small modules

No module in the application, the setup program or the tests may exceed a
fixed line cap; one just beneath it fails too. Build scripts are exempt.

- **Rather than:** letting files grow.
- **Gains:** modules are split at real seams before they are crowded.
- **Costs:** many small files.

### Background work reports back on the interface thread

The update check and the release import run off the interface thread. Their
results cross back on signals bound to objects living on the interface thread.
The import dialog never closes while its work runs; an update answer that
arrives after its window has gone is dropped.

- **Rather than:** callbacks that would run on the worker's own thread.
- **Gains:** no widget is touched from the wrong thread; a worker never
  reports to a window or dialog that has gone.
- **Costs:** more ceremony around background work.

### Checks kept separate, guards proved by breaking them

The formatters, the linters and the test suite are separate commands, each
read by its exit code. Every structural guard was proved by planting a
violation and watching it fail.

- **Rather than:** wiring the formatters into the suite; assuming a guard
  works because it passes.
- **Gains:** each failure names its own cause; a guard is known to catch what
  it claims to.
- **Costs:** several commands to remember to run; every new guard costs a
  deliberate breakage before it is trusted.
