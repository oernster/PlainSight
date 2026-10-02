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
an editor the reader chooses. A structural test names the only modules
allowed to write anything at all: the settings store, the store for imported
release notes and the one helper both of them write through.

- **Rather than:** a viewer with editing built in.
- **Gains:** looking at a folder cannot change it; the promise is a test
  result rather than a habit.
- **Costs:** every correction means a trip to another program.

### Any folder of documents, not one kind of file

A document is any file whose suffix names a kind PlainSight reads: Markdown,
plain text, HTML, Word and PDF. It began as a viewer for Claude skills,
hard-wired to one file name.

- **Rather than:** discovery tied to skill folders, which listed nothing in a
  folder of ordinary notes.
- **Gains:** notes, project documentation and skills are read the same way
  with no configuration.
- **Costs:** five readers to maintain where there was one.

### What PlainSight deliberately is not

It is not an editor, a search tool or a GitHub client. It indexes nothing; it
reads the folder when it is opened and again when the window comes back to
the front.

- **Rather than:** an all-purpose document workbench.
- **Gains:** a small surface held to a high bar.
- **Costs:** searching across documents needs another tool.

### Specification before code

The design plan is written as numbered requirements; the release notes
import has its own specification in which every requirement names the test
that verifies it, with a list of what is deliberately out of scope.

- **Rather than:** building first and describing afterwards.
- **Gains:** a ruled-out idea stays ruled out; a claim in the docs is one a
  test holds.
- **Costs:** keeping the specifications true is work of its own; several
  documentation passes have been spent correcting claims that had drifted.

## Reading only what was asked

### Nothing is read until a folder is chosen

There is no default folder and no first-run scan. A fresh install opens on
an empty tree and an invitation, having listed no directory at all.

- **Rather than:** opening on the Claude skills folder, as it once did.
- **Gains:** reading somebody's files is theirs to authorise; an unasked walk
  of a home directory never happens.
- **Costs:** a first run shows nothing until the reader acts.

### The chooser opens on the home directory

The folder chooser starts at the last folder taken, else the home directory.
Where it opens is kept apart from what is read: a folder offered in a dialog
has not been read.

- **Rather than:** the Claude skills folder, a dotted directory belonging to
  another application; the Documents folder, which macOS gates by name.
- **Gains:** the starting place raises no permission prompt on any of the
  three operating systems.
- **Costs:** the documents folder is one row down rather than open already.

### A neighbouring folder only where it is implied

The plugins tree beside a Claude skills folder is read as a second root only
when the chosen folder is a skills directory inside a `.claude` one. Any
other folder is read on its own.

- **Rather than:** reading the sibling called plugins beside any chosen
  folder, which once meant choosing a notes folder walked whatever sat next
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

There is no fallback to the first row. The pane opens saying "Select a
document".

- **Rather than:** selecting the first document, which chose one on every
  window activation; the pane reads itself down the page, so it was scrolling
  through a file nobody had opened.
- **Gains:** what is on screen is always what the reader asked for.
- **Costs:** one more click on a first visit.

### Fresh on every return to the window

The library is read again whenever the window is activated. There is no file
watcher and no polling thread.

- **Rather than:** watching the folders for changes.
- **Gains:** a reader who leaves to edit a document comes back to the current
  text; nothing runs in the background.
- **Costs:** the listing is paid for on every activation, which is why
  listing has to stay cheap.

### Bodies fetched when opened, not when listed

A listing keeps what each document says about itself and a fingerprint of
its file (size and modification time), never its text. The text is read for
the one document that is opened.

- **Rather than:** holding every body in the library. Measured over a skills
  tree, that retained 859.6KB of text to show one document; it is now 42.2KB.
- **Gains:** listing forty PDFs of twelve pages takes 7ms where extracting
  them all took 515ms; a document left on screen is never read off disk again.
- **Costs:** a document that has gone by the time it is opened has to say so
  rather than show a blank page.

### A document that cannot be read is still listed

A locked, damaged or unreadable file keeps its row. The reason is shown in
place of the body; a password-protected PDF says so on its row before it is
opened.

- **Rather than:** a dialog; leaving the file out.
- **Gains:** the reader sees everything that is there and why some of it
  cannot be read.
- **Costs:** none recorded.

### Somebody else's code and empty files hidden by default

While the tree filter is on, which it is until the reader turns it off,
folders named `venv` or `node_modules` are passed over and documents holding
no text are left out. A folder left with nothing to read goes too. Emptiness
is judged only from what listing already cost, so a PDF is never judged. A
document opened on its own is never filtered.

- **Rather than:** a right-click menu on the tree with the filter off by
  default, which it replaced.
- **Gains:** licence and metadata files from installed packages stay out of
  the tree.
- **Costs:** an empty PDF still shows; a document the reader wanted inside one
  of those folders needs the filter turned off.

## Documents and what they become

### One home for the kinds

Which suffixes are read, whether a kind declares fields, how its text reaches
the screen and what it is called in the status bar all live on one
enumeration. The reader for each kind is written out by hand in the
composition root rather than derived; a structural test requires every kind
to have one.

- **Rather than:** lists of suffixes held by each part that cares.
- **Gains:** the chooser, discovery and rendering cannot disagree; a kind
  added without a reader fails a test rather than being read by the wrong one.
- **Costs:** adding a kind touches two places on purpose.

### Three ways to the screen rather than a flag

A body is laid out for the page, kept exactly as typed or handed over as the
HTML it already is.

- **Rather than:** a boolean, which carried two meanings and had nowhere to
  put HTML.
- **Gains:** each kind says plainly what happens to it.
- **Costs:** none recorded.

### Plain text is shown exactly as typed

A text file is escaped into a preformatted block and never passed through the
Markdown renderer.

- **Rather than:** rendering it as Markdown, which would turn a line of
  hyphens into a heading rule and lose the author's line breaks.
- **Gains:** three hyphens in a text file are three hyphens.
- **Costs:** a text file that happens to be written in Markdown is shown as
  source.

### HTML is shown as the page it is; nothing in it runs

An HTML document is handed to the reading surface untouched. Scripts neither
run nor appear as text; htmx attributes are inert; a picture held at a web
address is not fetched. Tests pin all three, the last against a real server
on the loopback interface.

- **Rather than:** parsing the page to write it back, which would lose
  whatever the parser did not understand on every pass.
- **Gains:** a document somebody sent cannot act on the machine or reach the
  network.
- **Costs:** a page that needs scripts or remote pictures shows only the text
  around them.

### Word documents become HTML, not Markdown

A Word document is converted to HTML as it is read, at the boundary, so the
reading pane never learns where it came from. Headings, paragraphs, lists,
tables and emphasis cross; presentation does not.

- **Rather than:** Markdown, the first answer. Text that means nothing in Word
  became syntax on the way through: three paragraphs of a real CV indented
  with four spaces arrived as blocks of code. Escaping into HTML is total,
  where guarding Markdown against each such case has no end.
- **Gains:** nothing an author typed can be misread as markup; measured on a
  real CV, 11190 characters went in and 11190 came out.
- **Costs:** fonts, colours and page layout are not carried across.

### A Word table must have something to tabulate

A table is drawn as a table only with more than one row and more than one
column; anything else gives up its cells as the blocks of text they hold.
Runs sharing their emphasis are joined before they are marked.

- **Rather than:** drawing every table as one. Word lays pages out with tables
  as often as it tabulates; one single-row layout table on a real CV became a
  row 2550 characters long.
- **Gains:** a Word document reads as the document it looks like.
- **Costs:** a genuine single-row or single-column table is shown as plain
  blocks.

### A PDF is rebuilt into the document its page was laid out to be

Every run of text is taken with its place, size and face; a line set larger
than the body becomes a heading, a bold line is emphasised, a line opening
with a bullet is an item and running lines of body text are one paragraph.
Every threshold was measured on real files. A page that cannot be rebuilt
falls back to its plain words, asked first for their layout.

- **Rather than:** the words alone, which turned a real CV into a wall of
  monospace with every heading and bullet gone.
- **Gains:** a PDF reads like the rest; a failure costs the layout rather than
  the page.
- **Costs:** a form's grid becomes reading order. No fonts, rules or pictures
  come across; a scan yields no text at all.

### A reader never takes the application down

The Word and PDF readers catch every exception when opening a file, each
marked with its reason. They parse files somebody else chose, through
libraries with no contract about what they raise.

- **Rather than:** catching a list of the exception types seen so far.
- **Gains:** a broken file costs its own row, never the session.
- **Costs:** a genuine fault inside a reader is reported as an unreadable file.

### A wall of text gets somewhere for the eye to rest

An over-long passage is shown in groups of whole sentences with a gap between
them; an inventory with no sentence ends is broken at the divisions its
author did write. Code, headings, tables, quotations and bracketed asides are
never broken. A test takes the breaks out again and requires the original
text character for character.

- **Rather than:** showing very long paragraphs as they are; rewriting them.
- **Gains:** measured over a real library, the longest block a reader meets
  fell from 5604 characters to 1893; nothing is added, removed or reordered.
- **Costs:** the breaks are PlainSight's, not the author's.

### Long declared fields follow the body

A frontmatter value too long for a header row is lifted out and given its
own section after the document.

- **Rather than:** showing every field above the body; the longest measured
  ran to 11717 characters on one line and buried the document beneath it.
- **Gains:** the reader lands on the text they opened.
- **Costs:** a long field is found at the foot rather than the head.

### The status bar counts the text, not the file

The foot of the window names the kind of document at the left and counts its
characters and lines at the right. The count is of the text being read: a
Markdown document beneath its declared fields, a PDF or Word document as what
was read out of it. A document that could not be read names its kind and
carries no count.

- **Rather than:** a byte count of the file.
- **Gains:** the figure means the same thing for every kind.
- **Costs:** none recorded.

## The network

### Two requests of its own, never a third

PlainSight asks GitHub whether a newer release of itself exists. It also asks
GitHub's public API for a repository's releases when the reader imports them.
It opens no other connection and carries no telemetry. The donate button, a
link clicked inside a document and the Download button on an update prompt
each hand an address to the desktop for the browser to fetch.

- **Rather than:** a reader that fetches on a document's behalf; usage
  reporting.
- **Gains:** nothing leaves the machine without the reader's knowledge.
- **Costs:** no usage figures to steer development.

### Update checks: daily, quiet unless there is news

A check runs three seconds after the window opens and once a day while it
stays open, off the interface thread, with a five second limit and no
retries. It asks for the latest published release only, so a pre-release or
draft is never offered. A check nobody asked for speaks only when there is
something to download; one from the Help menu reports every outcome. A
version that is not dotted integers is never treated as newer. A skipped
release is one remembered tag.

- **Rather than:** no check at all; one that reports every outcome.
- **Gains:** updates are found without nagging; a malformed tag can never
  raise a prompt; skipping one release still lets the next one through.
- **Costs:** one unprompted request a day.

### No credential compiled in

Both requests go to GitHub without a token or an account.

- **Rather than:** an authenticated client.
- **Gains:** nothing to leak or to configure.
- **Costs:** the release import is held to GitHub's unauthenticated allowance
  of 60 requests an hour; an import spends one per hundred releases.

### The donation address is pinned literally

The donate address lives in one module as a plain constant. Structural tests
assert it character for character, assert its scheme and assert it appears
exactly once.

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

### Every request before any write

All of GitHub's answers are gathered and the whole refresh is planned before
a byte is written. A stop is honoured until writing starts and never after.

- **Rather than:** writing each release as it arrives.
- **Gains:** a failure asking GitHub, where nearly every failure is, leaves
  the disk untouched.
- **Costs:** a large history is held in memory until it is written.

### Never half a history

A first import is built in a hidden staging folder and renamed into place
only when complete. A refresh replaces each file whole and the record last.
Each import also sweeps staging folders that a dead import left untouched for
more than ten minutes.

- **Rather than:** writing into the collection directly.
- **Gains:** a failed first import leaves no collection; a failed refresh
  leaves every file either as it was or as it should be.
- **Costs:** the sweep waits ten minutes so that a second running copy's live
  staging folder is never taken.

### The reader's edits and withdrawn releases are kept

A file is known by its GitHub id and by a digest of what was last written to
it. A refresh rewrites a file only when it is unedited and GitHub's text
changed. A file the reader edited is kept and reported; a release GitHub no
longer lists keeps its file.

- **Rather than:** overwriting the folder with GitHub's current answer.
- **Gains:** once written, the files are the reader's own.
- **Costs:** edits are never merged with later changes on GitHub.

### A bad answer fails the import

A malformed entry in GitHub's answer fails the whole import rather than being
skipped. A page past 32 MiB is refused unread; a next page off GitHub's own
API host is refused; retrieval stops after a hundred pages.

- **Rather than:** importing what could be read.
- **Gains:** a history never silently misses a release.
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
there is no moment at which the position can be lost. When the height comes
back unchanged, as it does after a change of colour, the exact pixel is put
back; when it moved under a new size, the place is followed as an offset into
the text. The reading cycle then holds still for a moment.

- **Rather than:** setting the text on the live widget and restoring the
  place afterwards. Three attempts at that each guessed a different moment to
  restore and lost the place in a race.
- **Gains:** measured on a real display, the reader is back on the same pixel
  within 120ms after a change of colour.
- **Costs:** a more intricate redraw than setting text.

### An unchanged document is left alone

The library is read again on every activation. A document already on screen
and unchanged is not drawn again; one edited on disk is.

- **Rather than:** redrawing on every read, which sent the reader back to the
  top whenever they left the window.
- **Gains:** leaving to look something up costs nothing.
- **Costs:** a document must compare by value, which is what the fingerprint
  is for.

### A readable column that does not pen in code

Prose wraps at a readable line length, so a wide window buys margins rather
than longer lines. The cap is on where a line wraps rather than on how much
of the pane a page may use, so a code block or diagram too wide to wrap keeps
every pixel the window has. Text that arrived hard wrapped is left as it came.

- **Rather than:** shrinking the pane to the column, which penned wide diagrams
  into the same narrow strip with empty margin either side.
- **Gains:** prose reads comfortably and diagrams scroll sideways only when
  the window is genuinely too narrow.
- **Costs:** none recorded.

### A code block is one box

Every preformatted block sits in a table of one cell, in a monospace face
with whole box-drawing strokes, at its own line height.

- **Rather than:** the toolkit's own drawing, which painted the background
  line by line as a ragged staircase and picked Courier New, whose vertical
  strokes stop short.
- **Gains:** box-drawn diagrams join up; a wide block scrolls sideways as one
  rectangle.
- **Costs:** none recorded.

### The page reads itself

The document pane, the guide, About and both licences scroll gently on their
own and hand control back the moment the reader takes over. One set of
timings serves every surface; a page that fits is left still.

- **Rather than:** static pages.
- **Gains:** long text can be read hands free.
- **Costs:** none recorded.

### Three text sizes from one button

Medium, large and extra large are stepped by one button that wraps back to
the start. The sizes derive from one base and one step. The rendered page
declares no size of its own, so a change reaches the trays, the tree and the
page together.

- **Rather than:** a continuous scale.
- **Gains:** one button, walkable in a moment; the sizes cannot drift apart.
- **Costs:** no size between the three.

### A cycling button shows where a press leads

The appearance and text size buttons wear the state a press would move to.
The tree filter button is the exception: its picture shows the filter as it
stands (crossed out while everything is shown) while its tooltip offers
the press.

- **Rather than:** one rule for every toggle.
- **Gains:** each picture answers the question a reader asks of it.
- **Costs:** two conventions to learn.

### Full keyboard reach, rings only on controls

One explicit ring, declared by each tray in drawn order, reaches every
control; the reading pane joins it only while it overflows. A focus ring
belongs to a control, never to the tree or the page being read.

- **Rather than:** a focus order inferred from the layout; rings on panes.
- **Gains:** the whole application works without a mouse; clicking the text
  no longer draws a rectangle round the page.
- **Costs:** every new control needs its place in the ring.

### A help menu without a menu bar

The help button drops a menu of the Guide, About and Check for Updates, in
that order. It is popped by hand rather than set on the button.

- **Rather than:** a menu bar; a button carrying its menu, which grows an
  arrow indicator unlike every other picture in the tray.
- **Gains:** the tray stays a row of pictures; the Guide leads, since that is
  what most people opening the menu are asking.
- **Costs:** none recorded.

### The guide is drawn from the real icons

The guide names every tray control with the icon the tray itself draws,
through the same lookup and the same file-name constants. A missing asset
costs its picture and never the guide.

- **Rather than:** screenshots or descriptions of the pictures.
- **Gains:** the guide cannot drift from the interface.
- **Costs:** the guide is generated rather than freely laid out.

### Tooltips over an inactive window

Every top-level window is marked to show tooltips while another program has
focus, in the application and the setup program alike.

- **Rather than:** the toolkit's default of withholding them.
- **Gains:** hovering over PlainSight while working elsewhere still explains a
  control.
- **Costs:** none recorded.

### Contrast held by test

Light and dark each name their own ring and danger colours. Every pairing
that carries text is held to the WCAG AA ratio by a test, in the application
and the setup program.

- **Rather than:** judging colours by eye; three pairings looked deliberate
  and were under the ratio.
- **Gains:** a colour that cannot be read fails the suite rather than
  shipping.
- **Costs:** the dark theme needs a selection fill of its own, since one accent
  cannot both read on the panel and carry white.

### Folders open shut and stay as left

The tree remembers which folders the reader opened, by path. An empty record
is every folder shut, which is how a fresh install opens.

- **Rather than:** remembering which were closed; opening everything.
- **Gains:** a run opens as the last one closed; two folders sharing a name
  are never confused.
- **Costs:** a first visit to a deep tree takes some opening.

### A closed dialog is destroyed

A dialog is deleted when it closes rather than hidden.

- **Rather than:** keeping it parented and hidden. Ten openings of a licence
  left ten dialogs alive with ten reading cycles still ticking.
- **Gains:** nothing runs behind the window that the reader cannot see.
- **Costs:** a dialog is built afresh each time.

## Building and installing

### Nuitka

The application, the setup program and the macOS application are compiled
with Nuitka. The project moved to it from PyInstaller.

- **Rather than:** PyInstaller, which bundles an interpreter beside the
  source.
- **Gains:** one rule finds the bundled files in development and under a
  compiled build alike; the first release on it produced a setup program of
  63 megabytes.
- **Costs:** some packages must be named for inclusion by hand (the Markdown
  extensions, python-docx and pypdf), which ties the build to how those
  libraries load.

### Unused parts of Qt fenced out

The build excludes WebEngine, 3D, charts, multimedia and other Qt modules
nothing imports.

- **Rather than:** collecting the toolkit whole, which was measured at a
  726MB bundle under PyInstaller.
- **Gains:** nothing unused can creep in through an indirect import.
- **Costs:** a new Qt feature may need the fence moved.

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
footer per screen and ends every path in a verdict. Its progress bar is
weighted by measured time rather than step count. Every entry in the payload
is checked to land inside
the install folder before any is written.

- **Rather than:** a generic installer.
- **Gains:** one identity throughout; a crafted archive cannot write half its
  contents before it is caught.
- **Costs:** the setup program is PlainSight's own to maintain; its shortcut
  writer is still untested.

### Setup hands the foreground to what it starts

On Windows the setup program grants the foreground to the process it has just
started; the application asks for it by raising and activating its window.
Setup closes only after the start returns.

- **Rather than:** a plain show, which opened the window behind everything
  after a fresh install.
- **Gains:** the application comes to the front when setup finishes.
- **Costs:** neither half can be checked offscreen, so both are tested at the
  mechanism rather than by seeing the window come forward.

### Each platform builds on itself

Windows, macOS and Linux packages are built by their own scripts on their own
platforms. The macOS application and its disk image are signed and
notarised. The Flatpak fetches wheels for three platform tags, most specific
first.

- **Rather than:** cross-compiling; one platform tag, which found no wheel for
  lxml and failed before the build began.
- **Gains:** each package is built by the tools that know that platform.
- **Costs:** a machine of each kind and an Apple developer account; Windows
  is the one built regularly, so the other two can fall behind.

### Delivery tools kept out of the product's requirements

Nuitka and Pillow sit in the development requirements, since the application
imports neither. A structural test checks that every package imported and
every tool run as a subprocess is declared.

- **Rather than:** one requirements file; trusting an import scan, which
  cannot see a tool started as a subprocess.
- **Gains:** a fresh checkout can build as well as run.
- **Costs:** none recorded.

### Every dependency credited and held there

The About dialog credits every declared dependency with its licence. A test
compares the credit list with both requirements files.

- **Rather than:** a credit list written once and left. It had quietly fallen
  behind, crediting nothing for the packaging toolchain.
- **Gains:** a dependency cannot be added without being credited.
- **Costs:** the test checks the names; the licence text is still read by a
  person.

### One version, stamped into the site alone

`VERSION` is the single source of truth: the runtime reads it and the
website is stamped from it. No other document carries a version. The settings
file has a format number of its own. The stamper also tags each stylesheet
and script link with a hash of its content.

- **Rather than:** version numbers written into documents; tying the settings
  format to the application version.
- **Gains:** the application version can move without anything being done to
  a user's settings; a browser never pairs a new page with a stale stylesheet.
- **Costs:** the Linux build script does not call the stamper, so it is run by
  hand when that is the only build made.

### Icons from one master each

Every icon, tray mark and the donate mark is generated from a master image.
Nothing is upscaled: a master smaller than a wanted size is reported rather
than stretched. The masters stay out of the bundle.

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
each allowed to depend only inward. One composition root builds every
implementation; structural tests hold the boundaries and forbid anything
being built at import time. The interface finds its artwork through a port
rather than by reaching into infrastructure.

- **Rather than:** convention alone.
- **Gains:** the rules about documents, releases and updates are tested with
  no disk, network or screen.
- **Costs:** more modules and more explicit wiring.

### Paths are strings in the domain

The domain holds paths as plain strings and imports no filesystem, clock or
threading module. Moments in time are held as fixed UTC text.

- **Rather than:** path and date objects, which would bring those modules in.
- **Gains:** the purity rule holds without exception.
- **Costs:** conversion happens at the boundary every time.

### Complete coverage where it means something

Branch coverage must be total over the domain and application layers. The
infrastructure, the interface and the setup program carry real tests against
temporary directories and a real offscreen toolkit, outside that figure.

- **Rather than:** one figure over everything, which would mean either a weaker
  number or a list of exclusions.
- **Gains:** anything short of complete in the pure layers is a gap nobody
  chose.
- **Costs:** device, file and screen code relies on targeted tests.

### Small modules

No module in the application, the setup program or the tests may exceed four
hundred lines; one within the band just beneath that fails too. Build
scripts are exempt.

- **Rather than:** letting files grow.
- **Gains:** modules are split at real seams before they are crowded; the main
  window has twice been cut down this way.
- **Costs:** many small files.

### Background work reports back on the interface thread

The update check and the release import run on worker threads. Their results
cross back on signals bound to objects living on the interface thread. The
import dialog never closes while its worker runs; cancelling asks it to stop
and waits.

- **Rather than:** callbacks that would run on the worker's own thread.
- **Gains:** no widget is touched from the wrong thread; a worker never
  reports to a dialog that has gone.
- **Costs:** more ceremony around background work.

### Widgets a test built are destroyed

Both toolkit suites tear down through one shared helper that destroys what
each test built.

- **Rather than:** closing and scheduling deletion, which outside a running
  event loop destroyed nothing; the suite died with an access violation five
  times in fifteen.
- **Gains:** twenty five runs with no crash; the suite fell from about four
  minutes to five seconds.
- **Costs:** none recorded.

### Formatters as separate gates

`black`, `flake8`, `ruff` and the test suite are four commands, each read by
its exit code.

- **Rather than:** wiring the formatters into the suite as assertions.
- **Gains:** each failure names its own cause.
- **Costs:** four commands to remember to run.

### Guards proved by breaking them

Every structural guard was proved by planting a violation and reading the exit
code. Several first versions failed that test and were strengthened until they
bit.

- **Rather than:** assuming a guard works because it passes.
- **Gains:** a guard is known to catch what it claims to.
- **Costs:** every new guard costs a deliberate breakage and a second run
  before it is trusted.
