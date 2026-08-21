"""Tests for utils/storage.py -- file-based persistence."""

from __future__ import annotations

import json

from utils.storage import (
    STORAGE_PREFIX,
    clear_all_storage,
    load_from_storage,
    save_to_storage,
)


def test_save_and_load_roundtrip():
    assert save_to_storage("monthly_budget", 4200.0) is True
    assert load_from_storage("monthly_budget") == 4200.0


def test_load_missing_key_returns_default():
    assert load_from_storage("nonexistent_key", default="fallback") == "fallback"


def test_load_missing_key_returns_none_by_default():
    assert load_from_storage("nonexistent_key") is None


def test_save_overwrites_existing_key():
    save_to_storage("trusted_merchants", ["A"])
    save_to_storage("trusted_merchants", ["A", "B"])
    assert load_from_storage("trusted_merchants") == ["A", "B"]


def test_keys_are_namespaced_on_disk(_isolated_storage):
    save_to_storage("chat_history", [{"role": "user", "content": "hi"}])
    raw = json.loads(_isolated_storage.storage_file.read_text(encoding="utf-8"))
    assert f"{STORAGE_PREFIX}chat_history" in raw


def test_clear_all_storage_removes_file(_isolated_storage):
    save_to_storage("monthly_budget", 1000.0)
    assert _isolated_storage.storage_file.exists()
    assert clear_all_storage() is True
    assert not _isolated_storage.storage_file.exists()
    assert load_from_storage("monthly_budget", default=0.0) == 0.0


def test_corrupted_json_file_loads_as_empty(_isolated_storage):
    _isolated_storage.storage_file.parent.mkdir(parents=True, exist_ok=True)
    _isolated_storage.storage_file.write_text("{not valid json", encoding="utf-8")
    assert load_from_storage("anything", default="safe") == "safe"


def test_empty_file_is_not_treated_as_corrupted(_isolated_storage):
    _isolated_storage.storage_file.parent.mkdir(parents=True, exist_ok=True)
    _isolated_storage.storage_file.write_text("", encoding="utf-8")
    assert load_from_storage("anything", default="safe") == "safe"
    # A genuinely empty file must still be writable afterwards.
    assert save_to_storage("anything", "value") is True
    assert load_from_storage("anything") == "value"


def test_backend_falls_back_to_workspace_when_home_unwritable(tmp_path, monkeypatch):
    """`_resolve_storage_file` should not raise even if the home directory
    is not writable -- it should fall back to a workspace-local path."""
    import utils.storage as storage_module

    unwritable_home = tmp_path / "unwritable_home"
    unwritable_home.mkdir()
    unwritable_home.chmod(0o400)
    monkeypatch.setattr(storage_module.Path, "home", lambda: unwritable_home)
    monkeypatch.chdir(tmp_path)

    try:
        resolved = storage_module._resolve_storage_file()
        assert resolved.parent.name == ".wefinance"
    finally:
        unwritable_home.chmod(0o700)
