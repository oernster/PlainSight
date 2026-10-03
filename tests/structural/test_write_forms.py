"""The read-only guard, fed every write it claims to see.

Each form below writes, deletes or starts something by a route the audit found
the guard blind to or by the routes it always saw. Every one must be named by
the guard's predicate; a form it cannot name is a hole in the claim the
architecture makes about writing. The two directions of its stated limits are
pinned too, so a change to either is a decision rather than a drift.
"""

from __future__ import annotations

import ast

import pytest

from .write_capabilities import writing_calls

WRITE_FORMS = {
    "Path.write_text": "p.write_text('x')",
    "builtin open for writing": "open(p, 'w').write('x')",
    "Path.replace": "p.replace(q)",
    "Path.rename": "p.rename(q)",
    "os.open": "import os\nos.write(os.open(p, os.O_WRONLY | os.O_CREAT), b'x')",
    "os.open alone": "import os as system\nsystem.open(p, flags)",
    "open with a mode in a variable": "mode = 'w'\nopen(p, mode)",
    "aliased replace": "from os import replace as mv\nmv(a, b)",
    "aliased open": "from builtins import open as o\no(p, 'w')",
    "aliased module": "import shutil as s\ns.copyfile(a, b)",
    "shutil.copyfileobj": "import shutil\nshutil.copyfileobj(src, handle)",
    "QFile opened for writing": "QFile(p).open(QIODevice.WriteOnly)",
    "QFile opened for writing, no name": "file.open(QIODevice.OpenModeFlag.WriteOnly)",
    "QImage.save": "QImage(1, 1, fmt).save(p)",
    "sqlite3": "import sqlite3\nsqlite3.connect(p).execute('create table t(x)')",
    "subprocess": "import subprocess\nsubprocess.run(['cmd', '/c', 'echo x> f'])",
    "Path.open for writing": "p.open('w')",
    "Path.open with a mode keyword": "p.open(mode='a')",
    "Path.open with a mode in a variable": "p.open(mode=chosen)",
    "io.open": "import io\nio.open(p, 'w')",
    "codecs.open": "import codecs\ncodecs.open(p, 'w')",
    "os.makedirs": "import os\nos.makedirs(p)",
    "shutil.move": "import shutil\nshutil.move(a, b)",
    "shutil.copy2": "import shutil\nshutil.copy2(a, b)",
    "os.truncate": "import os\nos.truncate(p, 0)",
    "os.symlink": "import os\nos.symlink(a, b)",
    "tempfile.mkstemp": "import tempfile\ntempfile.mkstemp(dir=d)",
    "NamedTemporaryFile": "from tempfile import NamedTemporaryFile as T\nT()",
    "zipfile": "import zipfile\nzipfile.ZipFile(p, 'w')",
    "logging.FileHandler": "import logging\nlogging.FileHandler(p)",
    "QSettings": "QSettings('o', 'a').setValue('k', 1)",
    "QSaveFile": "f = QSaveFile(p)\nf.open(QIODevice.WriteOnly)\nf.commit()",
    "QDir.mkpath": "QDir().mkpath(p)",
    "QFile.copy": "QFile.copy(a, b)",
    "Qt write class imported": "from PySide6.QtCore import QSaveFile",
    "getattr with a built name": "import os\ngetattr(os, 'un' + 'link')(p)",
    "getattr with a write name": "getattr(p, 'unlink')()",
    "the builtin open rebound": "w = open\nw(p, 'w')",
    "os.system": "import os\nos.system('del x')",
    "os.startfile": "import os\nos.startfile(p)",
    "QProcess": "QProcess.startDetached('cmd', ['/c', 'del x'])",
    "exec": "exec('open(p, \"w\")')",
    "eval": "eval(text)",
    "__import__": "__import__('shutil').rmtree(p)",
    "importlib": "import importlib\nimportlib.import_module(name)",
    "ctypes": "import ctypes\nctypes.windll.kernel32.DeleteFileW(p)",
    "winreg": "import winreg\nwinreg.SetValueEx(key, name, 0, kind, value)",
    "file handle write": "handle.write(data)",
    "file handle writelines": "handle.writelines(lines)",
    "os.chmod": "import os\nos.chmod(p, 0)",
}

READING_FORMS = {
    "the external opener's port": "opener.open(address)",
    "a read with no mode": "p.open()",
    "a read with a read mode": "p.open('rb')",
    "QFile opened for reading": "file.open(QIODevice.ReadOnly)",
    "a dialog's exec": "dialog.exec()",
    "a scrollbar's setValue": "bar.setValue(0)",
    "a pattern compiled": "import re\nre.compile(r'x')",
    "getattr with a read name": "getattr(item, 'text')",
}


@pytest.mark.parametrize("form", sorted(WRITE_FORMS))
def test_every_write_form_is_named(form: str) -> None:
    assert writing_calls(ast.parse(WRITE_FORMS[form])) != set()


@pytest.mark.parametrize("form", sorted(READING_FORMS))
def test_a_form_that_writes_nothing_is_not_named(form: str) -> None:
    assert writing_calls(ast.parse(READING_FORMS[form])) == set()


def test_a_string_replace_is_named_all_the_same() -> None:
    """The stated limit in the other direction: a name cannot carry its type.

    A string's ``replace`` and the filesystem's share a name, so code outside
    the granted modules says ``html.escape`` or ``str.translate`` instead.
    """
    assert writing_calls(ast.parse("'a'.replace('a', 'b')")) != set()
