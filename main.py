"""The entry point the build scripts hand to PyInstaller.

It defers to the package's own composition root rather than wiring anything of
its own, so there is exactly one place where dependencies are constructed.
"""

from __future__ import annotations

from plainsight.__main__ import main

if __name__ == "__main__":
    raise SystemExit(main())
