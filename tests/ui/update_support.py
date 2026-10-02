"""What the update check suites share: the running version and a service.

Shared by the check's own tests and by the one holding what happens when the
window goes before the answer comes back.
"""

from __future__ import annotations

from plainsight.application.ports import ReleaseSource
from plainsight.application.update import UpdateService

CURRENT_VERSION = "0.1.0"
PLATFORM_KEY = "windows"


def a_service_over(source: ReleaseSource) -> UpdateService:
    """The update service as the window is given it, over any source."""
    return UpdateService(
        source=source, current_version=CURRENT_VERSION, platform_key=PLATFORM_KEY
    )
