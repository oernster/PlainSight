"""Session-wide setup. The platform is chosen before any Qt import happens."""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
