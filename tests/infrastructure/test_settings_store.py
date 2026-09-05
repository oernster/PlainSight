"""Remembering the root and the editor across runs."""

from __future__ import annotations

import json
from pathlib import Path

from plainsight.domain.settings import EditorChoice, FontSize, Settings
from plainsight.infrastructure.settings_store import FORMAT_VERSION, JsonSettingsStore

AN_EDITOR = EditorChoice(path="/usr/bin/vi", display_name="vi")


def test_nothing_written_yet_loads_the_defaults(tmp_path: Path) -> None:
    store = JsonSettingsStore(tmp_path / "settings.json")

    assert store.load() == Settings()


def test_what_was_saved_comes_back(tmp_path: Path) -> None:
    store = JsonSettingsStore(tmp_path / "nested" / "settings.json")

    store.save(Settings(documents_root="/skills", editor=AN_EDITOR))

    assert store.load() == Settings(documents_root="/skills", editor=AN_EDITOR)


def test_the_record_carries_its_format_version(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"

    JsonSettingsStore(path).save(Settings(documents_root="/skills"))

    assert json.loads(path.read_text(encoding="utf-8"))["version"] == FORMAT_VERSION


def test_settings_with_no_editor_round_trip(tmp_path: Path) -> None:
    store = JsonSettingsStore(tmp_path / "settings.json")

    store.save(Settings(documents_root="/skills"))

    assert store.load().editor is None


def test_a_file_that_is_not_json_loads_the_defaults(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    path.write_text("not json at all", encoding="utf-8")

    assert JsonSettingsStore(path).load() == Settings()


def test_json_that_is_not_a_record_loads_the_defaults(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    path.write_text("[1, 2, 3]", encoding="utf-8")

    assert JsonSettingsStore(path).load() == Settings()


def test_fields_of_the_wrong_shape_are_ignored(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    path.write_text(
        json.dumps({"documents_root": 7, "editor": "a string"}), encoding="utf-8"
    )

    assert JsonSettingsStore(path).load() == Settings()


def test_an_editor_record_missing_its_path_is_ignored(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    path.write_text(json.dumps({"editor": {"display_name": "vi"}}), encoding="utf-8")

    assert JsonSettingsStore(path).load().editor is None


def test_a_skipped_release_survives_a_round_trip(tmp_path: Path) -> None:
    store = JsonSettingsStore(tmp_path / "settings.json")

    store.save(Settings().with_skipped_update_version("0.2.0"))

    assert store.load().skipped_update_version == "0.2.0"


def test_a_file_written_before_the_update_check_reads_as_nothing_skipped(
    tmp_path: Path,
) -> None:
    path = tmp_path / "settings.json"
    path.write_text(
        json.dumps({"version": 1, "documents_root": "/skills"}), encoding="utf-8"
    )

    assert JsonSettingsStore(path).load().skipped_update_version == ""


def test_a_skipped_release_recorded_as_something_other_than_text_is_ignored(
    tmp_path: Path,
) -> None:
    path = tmp_path / "settings.json"
    path.write_text(
        json.dumps({"version": 1, "skipped_update_version": 3}), encoding="utf-8"
    )

    assert JsonSettingsStore(path).load().skipped_update_version == ""


def test_a_text_size_survives_a_round_trip(tmp_path: Path) -> None:
    store = JsonSettingsStore(tmp_path / "settings.json")

    store.save(Settings().with_font_size(FontSize.EXTRA_LARGE))

    assert store.load().font_size is FontSize.EXTRA_LARGE


def test_a_file_written_before_the_text_sizes_reads_as_the_default(
    tmp_path: Path,
) -> None:
    path = tmp_path / "settings.json"
    path.write_text(
        json.dumps({"version": 1, "documents_root": "/skills"}), encoding="utf-8"
    )

    assert JsonSettingsStore(path).load().font_size is FontSize.MEDIUM


def test_a_text_size_recorded_as_nonsense_reads_as_the_default(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    path.write_text(json.dumps({"version": 1, "font_size": 9}), encoding="utf-8")

    assert JsonSettingsStore(path).load().font_size is FontSize.MEDIUM
