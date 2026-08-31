"""Everything the setup program's own interface reads is staged for it.

The window reads its mark and both appearance marks from beside the payload,
not from inside the zipped bundle it has not extracted yet. A name the staging
step does not carry leaves the built setup program with a blank button, which
no offscreen test of the source tree would ever notice.
"""

from __future__ import annotations

from installer import bundled
from installer.build_payload import CARRIED_ASSETS

READ_BY_THE_WINDOW = (
    bundled.MARK_NAME,
    bundled.LIGHT_MODE_NAME,
    bundled.DARK_MODE_NAME,
)


def test_every_mark_the_window_reads_is_staged() -> None:
    assert [name for name in READ_BY_THE_WINDOW if name not in CARRIED_ASSETS] == []


def test_every_staged_asset_exists_in_the_repository() -> None:
    from installer.build_payload import PROJECT_ROOT

    missing = [
        name
        for name in CARRIED_ASSETS
        if not (PROJECT_ROOT / "assets" / name).is_file()
    ]

    assert missing == []
