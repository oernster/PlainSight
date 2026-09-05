"""The donation address, pinned where a typo cannot reach a supporter.

Asserted literally rather than by shape. A pattern check would pass a
transposed character in the payment id and send money to a page that is not
Oliver's, which is the one failure this test exists to prevent.
"""

from __future__ import annotations

import ast

from plainsight import version

from .layers import PACKAGE_ROOT, package_files, parse

ADDRESS = "https://www.paypal.com/ncp/payment/BCZF8TZTUGTEA"
REQUIRED_SCHEME = "https://"
IDENTITY_MODULE = "version.py"


def test_the_address_is_exactly_this() -> None:
    assert version.DONATE_URL == ADDRESS


def test_the_address_is_https() -> None:
    """A payment page reached over plain HTTP is not one to hand anybody."""
    assert version.DONATE_URL.startswith(REQUIRED_SCHEME)


def test_the_address_has_one_home() -> None:
    """A second copy drifts; the one that drifts is the one that misdirects.

    Occurrences are counted rather than files: a planted second copy inside the
    same module slipped past a per-file check, so the count is what is asserted.
    """
    occurrences = {
        path.name: path.read_text(encoding="utf-8").count(ADDRESS)
        for path in package_files()
        if ADDRESS in path.read_text(encoding="utf-8")
    }

    assert occurrences == {IDENTITY_MODULE: 1}


def test_it_is_a_module_level_constant_rather_than_computed() -> None:
    """Nothing builds it at runtime, so nothing can build it wrongly."""
    tree = parse(PACKAGE_ROOT / IDENTITY_MODULE)
    assigned = {
        target.id: statement.value
        for statement in tree.body
        if isinstance(statement, ast.Assign)
        for target in statement.targets
        if isinstance(target, ast.Name)
    }

    value = assigned.get("DONATE_URL")
    assert isinstance(value, ast.Constant)
    assert value.value == ADDRESS
