# Development

How to run PlainSight from source, build it on each platform and cut a release.
What the product does and why is in [README.md](README.md); how it is put
together is in [ARCHITECTURE.md](ARCHITECTURE.md); running and writing the tests
is in [TESTING.md](TESTING.md). Every command is PowerShell from the repository
root unless it is marked as a macOS or Linux one.

## Tools

| Tool | What for | Where from |
|---|---|---|
| Python 3.11 or newer | everything | [python.org](https://www.python.org/downloads/) |
| PySide6, markdown, python-docx, pypdf | the application | `requirements.txt` |
| pytest, pytest-cov, pytest-qt, black, flake8, ruff | the checks | `requirements-dev.txt` |
| Nuitka 4.2.1 or newer | the Windows and macOS builds | `requirements-dev.txt` |
| Pillow | the icon set | `requirements-dev.txt` |
| Xcode command-line tools, Homebrew, a Developer ID and a notarization profile | the macOS build | Apple; see Building |
| flatpak, flatpak-builder, the freedesktop runtime | the Linux build | installed by `build_flatpak.sh` when missing |

`requirements-dev.txt` does not include `requirements.txt`, so a development
environment installs both.

## Running from source

```powershell
python -m venv venv
venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt -r requirements-dev.txt
python -m plainsight
```

**A run from source uses your real settings.** PlainSight keeps its files in
`.plainsight` in your home directory: `settings.json` and the imported release
notes under `github-releases`. Nothing redirects that folder, so a run from
source reads and writes the same settings an installed copy does. The
application writes no log file.

## Building

Each platform builds on itself; none of the three cross-compiles.

**Windows.** Two scripts, in order:

```powershell
python buildexe.py
python buildinstaller.py
```

`buildexe.py`:

1. stops unless Nuitka 4.2.1 or newer is installed (`require_nuitka` in
   `build_utils.py`), before anything is touched;
2. stamps the version into the site under `docs/` (`stamp_version.py`);
3. removes the previous build;
4. compiles the entry point `main.py` with Nuitka as a deployment build, one
   job per logical core;
5. stages the result as `installer/payload/PlainSight/PlainSight.exe`.

`buildinstaller.py`:

1. makes the same Nuitka check;
2. stamps the version again;
3. zips the staged bundle into `installer/payload/PlainSight.zip` and copies
   beside it the files the setup program's own window reads (`VERSION`,
   `INSTALLER_LICENSE` and four pictures), through `installer/build_payload.py`;
4. compiles `installer/app.py` with Nuitka into one compressed executable that
   carries the payload;
5. moves it to `dist-installer/PlainSightSetup.exe`, retrying while antivirus or
   Explorer still holds the old one open.

A missing or older Nuitka stops either script with the version found, the
version wanted and the install command.

**macOS** (run on a Mac):

```bash
python builddmg.py
```

Compiles with Nuitka after checking its version, signs every nested binary then
the bundle with a Developer ID, notarizes and staples the bundle, then builds
the image and signs, notarizes, staples and assesses that too, producing
`PlainSight.dmg`. Notarization is not optional. Credentials come from a keychain
profile stored once with `xcrun notarytool store-credentials`; the docstring at
the top of `builddmg.py` lists the variables that override it.
`ALLOW_UNNOTARIZED=1` builds without notarizing, for local testing only.

**Linux:**

```bash
./build_flatpak.sh
./clean_flatpak.sh
```

`build_flatpak.sh` installs flatpak and flatpak-builder through the system's
package manager when they are missing, adds Flathub and installs the runtime,
fetches every wheel on the host first so the sandbox build reaches the network
for nothing, then writes `plainsight.flatpak`. It generates its manifest and
packaging helpers as it goes, so only the script is committed.
`clean_flatpak.sh` uninstalls the application and removes those build artefacts
and nothing else.

## Generated assets

`python generate_icons.py` reads the master `plainsight.png` at the repository
root and writes the whole icon set into `assets/`, along with the tray marks and
the donate mark. Change the artwork by replacing the master and running it
again.

## Versioning

`VERSION` at the repository root is the only place a version is written. The
runtime reads it, `pyproject.toml` reads it dynamically and `stamp_version.py`
writes it into the delimited tokens of the site under `docs/`. The three Python
build scripts stamp before they build; `build_flatpak.sh` does not, so run
`python stamp_version.py` by hand when a Linux build is the only one made. It
is idempotent and also puts a content hash on every local stylesheet and script
link in the site, so a browser cannot pair a fresh page with a stale cached
stylesheet.

## Cutting a release

1. Bump `VERSION`.
2. Run the checks in [TESTING.md](TESTING.md); all four must exit 0.
3. Build on each platform as above.
4. Publish the artefacts as a GitHub release tagged `v` plus the version, for
   example `v1.2.0`. The update check reads the version from the release tag,
   dropping a leading `v` where there is one.

## Standing rules

- The layers point inward: `ui` sees `application` and `domain`,
  `application` sees `domain`, `infrastructure` implements the application's
  ports and the domain sees nothing. Only the composition
  root in `plainsight/__main__.py` builds an implementation.
- PlainSight never writes to a document the reader opened; only the named
  writers write anything.
- No module goes over 400 lines, nor sits in the band just below it.
- Every third-party package used is declared and credited in About.

Each of these is held by a structural test; [TESTING.md](TESTING.md) names
them.

---

See also [README.md](README.md), [ARCHITECTURE.md](ARCHITECTURE.md) and
[TESTING.md](TESTING.md).
