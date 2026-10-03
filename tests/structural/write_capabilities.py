"""Every way a source file could write, delete or start something, by name.

The read-only guard grants each module the capabilities it needs and refuses
the rest; this module is how it sees which capabilities a file uses. A
capability is a short label for one form: a method named like a write, a module
that exists to write or to run things, a Qt class that does, the builtin
``open`` in any guise, an ``open`` given a mode that writes; a dynamic call
that would hide any of these from a reader.

What it cannot see is stated rather than implied. It reads names, not types,
so a string's ``replace`` reads as the filesystem's; a third-party library or
Qt itself writing on the application's behalf is invisible to it; a write
reached through an object handed in from outside, under a name not listed
here, is invisible too. It is a check on this package's own source, not a
sandbox. The Flatpak's read-only home is the enforcement on Linux.
"""

from __future__ import annotations

import ast
import re

# Methods named for what they do to a file, a directory or a process.
WRITE_METHODS = frozenset(
    {
        "write_text",
        "write_bytes",
        "write",
        "writelines",
        "mkdir",
        "makedirs",
        "unlink",
        "rmdir",
        "removedirs",
        "replace",
        "rename",
        "renames",
        "touch",
        "remove",
        "rmtree",
        "truncate",
        "symlink",
        "symlink_to",
        "link",
        "hardlink_to",
        "copy2",
        "copyfile",
        "copyfileobj",
        "copytree",
        "copymode",
        "copystat",
        "move",
        "chmod",
        "chown",
        "utime",
        "mkstemp",
        "mkdtemp",
        "mkpath",
        "save",
        "system",
        "popen",
        "startfile",
        "execv",
        "execve",
        "execl",
        "execle",
        "execlp",
        "execvp",
        "execvpe",
        "spawnl",
        "spawnv",
        "spawnve",
        "posix_spawn",
    }
)

# Modules that exist to write, to run things or to reach past Python.
WRITE_MODULES = frozenset(
    {
        "builtins",
        "bz2",
        "codecs",
        "ctypes",
        "dbm",
        "gzip",
        "importlib",
        "io",
        "logging",
        "lzma",
        "mmap",
        "msvcrt",
        "multiprocessing",
        "pty",
        "shelve",
        "shutil",
        "sqlite3",
        "subprocess",
        "tarfile",
        "tempfile",
        "winreg",
        "zipfile",
        "_winapi",
    }
)

# Qt classes that write files, keep settings on disk or start processes.
WRITE_CLASSES = frozenset(
    {
        "QDir",
        "QFile",
        "QFileDevice",
        "QImageWriter",
        "QLockFile",
        "QPdfWriter",
        "QProcess",
        "QSaveFile",
        "QSettings",
        "QTemporaryDir",
        "QTemporaryFile",
        "QTextDocumentWriter",
    }
)

# Builtins that write, that run text or that fetch an attribute out of sight.
WRITE_BUILTINS = frozenset({"open", "exec", "eval", "compile", "__import__"})
DYNAMIC_LOOKUP = "getattr"
# Modules whose own ``open`` writes as readily as it reads.
OPENING_MODULES = frozenset({"os", "io", "codecs", "gzip", "bz2", "lzma"})
OPEN = "open"
MODE_KEYWORD = "mode"
# A file mode is these letters; it writes when it holds any of the second set.
MODE_LETTERS = re.compile(r"^[rwaxbtU+]+$")
WRITING_LETTERS = frozenset("wax+")
# Qt's open flags that write.
WRITING_FLAGS = frozenset({"WriteOnly", "ReadWrite", "Append", "Truncate", "NewOnly"})
LOOKUP_NAME_POSITION = 1


def writing_calls(tree: ast.Module) -> set[str]:
    """Every write capability this file uses, each as a short label."""
    aliases = _module_aliases(tree)
    found: set[str] = set()
    for node in ast.walk(tree):
        found.update(_imports(node))
        found.update(_names(node))
        if isinstance(node, ast.Call):
            found.update(_call(node, aliases))
    return found


def _imports(node: ast.AST) -> set[str]:
    if isinstance(node, ast.Import):
        return {
            f"import {alias.name}"
            for alias in node.names
            if alias.name.split(".")[0] in WRITE_MODULES
        }
    if not isinstance(node, ast.ImportFrom):
        return set()
    found = set()
    if (node.module or "").split(".")[0] in WRITE_MODULES:
        found.add(f"import {node.module}")
    writing = WRITE_METHODS | WRITE_CLASSES | WRITE_BUILTINS
    found.update(f"import {a.name}" for a in node.names if a.name in writing)
    return found


def _names(node: ast.AST) -> set[str]:
    """A write class or a writing builtin, mentioned at all."""
    if isinstance(node, ast.Name) and node.id in WRITE_CLASSES | WRITE_BUILTINS:
        return {node.id}
    if isinstance(node, ast.Attribute) and node.attr in WRITE_CLASSES:
        return {node.attr}
    return set()


def _call(node: ast.Call, aliases: dict[str, str]) -> set[str]:
    target = node.func
    if isinstance(target, ast.Name) and target.id == DYNAMIC_LOOKUP:
        return _lookup(node)
    if not isinstance(target, ast.Attribute):
        return set()
    if target.attr in WRITE_METHODS:
        return {target.attr}
    if target.attr != OPEN:
        return set()
    if isinstance(target.value, ast.Name) and aliases.get(target.value.id) in (
        OPENING_MODULES
    ):
        return {f"{aliases[target.value.id]}.open"}
    return {"open for writing"} if _opens_for_writing(node) else set()


def _lookup(node: ast.Call) -> set[str]:
    """``getattr`` by a name nobody can read; else by a write's name."""
    if len(node.args) <= LOOKUP_NAME_POSITION:
        return {"getattr"}
    name = node.args[LOOKUP_NAME_POSITION]
    if not (isinstance(name, ast.Constant) and isinstance(name.value, str)):
        return {"getattr"}
    return {f"getattr {name.value}"} if name.value in WRITE_METHODS else set()


def _opens_for_writing(node: ast.Call) -> bool:
    """An ``open`` handed a mode or a flag that writes; else a mode out of sight."""
    for keyword in node.keywords:
        if keyword.arg == MODE_KEYWORD and not _reads_only(keyword.value):
            return True
    for argument in node.args:
        is_text = isinstance(argument, ast.Constant) and isinstance(argument.value, str)
        if is_text and not _reads_only(argument):
            return True
        if any(
            isinstance(part, ast.Attribute) and part.attr in WRITING_FLAGS
            for part in ast.walk(argument)
        ):
            return True
    return False


def _reads_only(mode: ast.expr) -> bool:
    """Whether a mode is a literal that opens for reading and nothing else.

    A string that is not a mode at all, an address handed to the opener port,
    reads as nothing being opened here.
    """
    if not (isinstance(mode, ast.Constant) and isinstance(mode.value, str)):
        return False
    if not MODE_LETTERS.match(mode.value):
        return True
    return not WRITING_LETTERS & set(mode.value)


def _module_aliases(tree: ast.Module) -> dict[str, str]:
    """Each name a module was imported under, mapped to the module."""
    aliases: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                aliases[alias.asname or alias.name] = alias.name
    return aliases
