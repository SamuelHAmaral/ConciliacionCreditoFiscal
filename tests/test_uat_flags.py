"""Tests for developer UAT flag resolution."""

from __future__ import annotations

from pathlib import Path

import pytest

from ui.uat_flags import resolve_run_uat


def test_resolve_run_uat_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("RECONCILIATION_RUN_UAT", raising=False)
    monkeypatch.setattr("ui.uat_flags.load_settings", lambda _root: {})
    monkeypatch.setenv("RECONCILIATION_RUN_UAT", "1")
    assert resolve_run_uat(tmp_path) is True


def test_resolve_run_uat_settings(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("RECONCILIATION_RUN_UAT", raising=False)
    monkeypatch.setattr("ui.uat_flags.load_settings", lambda _root: {"run_uat": "1"})
    assert resolve_run_uat(tmp_path) is True


def test_resolve_run_uat_legacy_settings_key(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("RECONCILIATION_RUN_UAT", raising=False)
    monkeypatch.setattr("ui.uat_flags.load_settings", lambda _root: {"verify_calculations": "1"})
    assert resolve_run_uat(tmp_path) is True


def test_resolve_run_uat_off(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("RECONCILIATION_RUN_UAT", raising=False)
    monkeypatch.setattr("ui.uat_flags.load_settings", lambda _root: {})
    assert resolve_run_uat(tmp_path) is False
