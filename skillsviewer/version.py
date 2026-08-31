"""The application's identity. The version comes from the VERSION file only."""

from __future__ import annotations

from .infrastructure.resources import read_version

APP_NAME = "Skills Viewer"
APP_TAGLINE = "A reader for the skills used by Claude AI"
APP_AUTHOR = "Oliver Ernster"
APP_COPYRIGHT = "© Oliver Ernster"

# Where the donate button sends a browser. It is handed to the desktop rather
# than fetched, so nothing is opened from here. The one address the application
# does fetch for itself lives beside the update check that asks it.
DONATE_URL = "https://www.paypal.com/ncp/payment/BCZF8TZTUGTEA"

__version__ = read_version()
