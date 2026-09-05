"""The architecture invariant, enforced rather than described.

UI -> Application -> Domain <- Infrastructure. Nothing reaches inwards past its
own layer and nothing reaches outwards at all.
"""

from __future__ import annotations

from .layers import (
    LAYERS,
    PERMITTED_IMPORTS,
    imported_modules,
    layer_of,
    parse,
    source_files,
)


def test_no_layer_imports_a_layer_it_may_not_see() -> None:
    offences: list[str] = []
    for layer in LAYERS:
        for path in source_files(layer):
            for module in imported_modules(parse(path), path):
                imported = layer_of(module)
                if imported is None or imported == layer:
                    continue
                if imported not in PERMITTED_IMPORTS[layer]:
                    offences.append(f"{path.name}: {layer} imports {imported}")

    assert offences == []


def test_the_domain_reads_nothing_from_outside_itself() -> None:
    forbidden = {
        "os",
        "sys",
        "pathlib",
        "logging",
        "time",
        "datetime",
        "random",
        "threading",
        "subprocess",
        "json",
        "tempfile",
    }
    offences: list[str] = []
    for path in source_files("domain"):
        for module in imported_modules(parse(path), path):
            if module.split(".")[0] in forbidden:
                offences.append(f"{path.name} imports {module}")

    assert offences == []


def test_the_application_layer_imports_no_third_party_package() -> None:
    permitted_roots = {
        "plainsight",
        "__future__",
        "os",
        "typing",
        "dataclasses",
        "abc",
        "enum",
    }
    offences: list[str] = []
    for path in source_files("application"):
        for module in imported_modules(parse(path), path):
            root = module.split(".")[0]
            if root and root not in permitted_roots:
                offences.append(f"{path.name} imports {module}")

    assert offences == []
