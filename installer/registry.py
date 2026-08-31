"""The uninstall record, written under HKCU so no administrator is needed.

Everything here is Windows only. On any other platform the reads report nothing
and the writes do nothing, so the module imports and the pure layers above it
can be exercised anywhere.
"""

from __future__ import annotations

import pathlib
import sys

from installer import actions
from installer.plan import InstallPlan

UNINSTALL_KEY = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\SkillsViewer"
PUBLISHER = "Oliver Ernster"
NO_MODIFY = 1
NO_REPAIR = 1

IS_WINDOWS = sys.platform == "win32"


def _winreg():  # pragma: no cover - the import is the platform gate itself
    import winreg

    return winreg


def read_registered() -> dict[str, str]:
    """What the Apps list records about this application, if anything."""
    if not IS_WINDOWS:
        return {}
    winreg = _winreg()
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, UNINSTALL_KEY) as key:
            return _read_values(winreg, key)
    except OSError:
        return {}


def _read_values(winreg, key) -> dict[str, str]:  # pragma: no cover - Windows only
    values: dict[str, str] = {}
    index = 0
    while True:
        try:
            name, value, _kind = winreg.EnumValue(key, index)
        except OSError:
            return values
        values[name] = str(value)
        index += 1


def register(plan: InstallPlan) -> None:  # pragma: no cover - Windows only
    """Write the Apps list record for this install."""
    if not IS_WINDOWS:
        return
    winreg = _winreg()
    icon = plan.target / "assets" / "skillsviewer.ico"
    entries = {
        "DisplayName": actions.APP_DISPLAY_NAME,
        "DisplayVersion": plan.version,
        "InstallLocation": str(plan.target),
        "UninstallString": f'"{actions.uninstaller_path(plan)}" --uninstall',
        "DisplayIcon": str(icon),
        "Publisher": PUBLISHER,
    }
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, UNINSTALL_KEY) as key:
        for name, value in entries.items():
            winreg.SetValueEx(key, name, 0, winreg.REG_SZ, value)
        winreg.SetValueEx(key, "NoModify", 0, winreg.REG_DWORD, NO_MODIFY)
        winreg.SetValueEx(key, "NoRepair", 0, winreg.REG_DWORD, NO_REPAIR)
        winreg.SetValueEx(
            key,
            "EstimatedSize",
            0,
            winreg.REG_DWORD,
            actions.install_size_kb(plan.target),
        )


def unregister() -> None:  # pragma: no cover - Windows only
    """Remove the Apps list record, tolerating one that is already gone."""
    if not IS_WINDOWS:
        return
    winreg = _winreg()
    try:
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, UNINSTALL_KEY)
    except OSError:
        return


def write_shortcut(
    link: pathlib.Path, target: pathlib.Path
) -> bool:  # pragma: no cover - Windows only
    """Write one shortcut through the shell; False when the shell declined."""
    if not IS_WINDOWS:
        return False
    try:
        import pythoncom  # noqa: F401
        from win32com.client import Dispatch
    except ImportError:
        return _write_shortcut_by_script(link, target)
    link.parent.mkdir(parents=True, exist_ok=True)
    shell = Dispatch("WScript.Shell")
    shortcut = shell.CreateShortCut(str(link))
    shortcut.Targetpath = str(target)
    shortcut.WorkingDirectory = str(target.parent)
    shortcut.IconLocation = str(target)
    shortcut.save()
    return True


def _write_shortcut_by_script(
    link: pathlib.Path, target: pathlib.Path
) -> bool:  # pragma: no cover - Windows only
    """The fallback when the COM bindings are not in the bundle."""
    import subprocess
    import tempfile

    script = (
        f"$s = (New-Object -ComObject WScript.Shell).CreateShortcut('{link}');"
        f"$s.TargetPath = '{target}'; $s.WorkingDirectory = '{target.parent}';"
        f"$s.IconLocation = '{target}'; $s.Save()"
    )
    link.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", suffix=".ps1", delete=False) as handle:
        handle.write(script)
        script_path = handle.name
    completed = subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            script_path,
        ],
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        capture_output=True,
        check=False,
    )
    pathlib.Path(script_path).unlink(missing_ok=True)
    return completed.returncode == 0


def remove_shortcut(link: pathlib.Path) -> None:
    """Remove one shortcut, tolerating one that is already gone."""
    link.unlink(missing_ok=True)
