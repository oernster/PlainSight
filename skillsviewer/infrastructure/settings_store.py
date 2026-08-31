"""Remembers the root and the editor in one small versioned JSON file.

The write is atomic: a temporary file beside the target, then a replace, so a
process that dies halfway leaves the previous settings intact rather than a
half-written file the next run cannot read.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from ..domain.settings import (
    Appearance,
    EditorChoice,
    InvalidEditorChoice,
    Settings,
)

FORMAT_VERSION = 1
VERSION_KEY = "version"
ROOT_KEY = "skills_root"
EDITOR_KEY = "editor"
EDITOR_PATH_KEY = "path"
EDITOR_NAME_KEY = "display_name"
APPEARANCE_KEY = "appearance"


class JsonSettingsStore:
    """Settings held as JSON at a path chosen by the composition root."""

    def __init__(self, path: Path) -> None:
        self._path = path

    def load(self) -> Settings:
        """What was remembered; the defaults when nothing readable was there."""
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return Settings()
        if not isinstance(raw, dict):
            return Settings()
        return Settings(
            skills_root=_text(raw.get(ROOT_KEY)),
            editor=_editor(raw.get(EDITOR_KEY)),
            appearance=Appearance.of(_text(raw.get(APPEARANCE_KEY))),
        )

    def save(self, settings: Settings) -> None:
        """Write these settings, replacing whatever was there."""
        payload = {
            VERSION_KEY: FORMAT_VERSION,
            ROOT_KEY: settings.skills_root,
            APPEARANCE_KEY: settings.appearance.value,
            EDITOR_KEY: (
                None
                if settings.editor is None
                else {
                    EDITOR_PATH_KEY: settings.editor.path,
                    EDITOR_NAME_KEY: settings.editor.display_name,
                }
            ),
        }
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._write_atomically(json.dumps(payload, indent=2))

    def _write_atomically(self, text: str) -> None:
        """Write beside the target, then move it into place in one step."""
        handle, temporary = tempfile.mkstemp(dir=str(self._path.parent))
        try:
            with os.fdopen(handle, "w", encoding="utf-8") as stream:
                stream.write(text)
            os.replace(temporary, self._path)
        except OSError:
            os.unlink(temporary)
            raise


def _text(value: object) -> str:
    """A string field; an empty string when it was anything else."""
    return value if isinstance(value, str) else ""


def _editor(value: object) -> EditorChoice | None:
    """An editor choice; None when the record cannot describe one."""
    if not isinstance(value, dict):
        return None
    try:
        return EditorChoice(
            path=_text(value.get(EDITOR_PATH_KEY)),
            display_name=_text(value.get(EDITOR_NAME_KEY)),
        )
    except InvalidEditorChoice:
        return None
