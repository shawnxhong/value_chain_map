"""Scaffold tests for configuration loading."""

from __future__ import annotations

import pytest

from vcm.config import Settings, get_settings


def test_defaults() -> None:
    s = Settings()
    assert s.extract_model == "claude-sonnet-4-6"
    assert s.verify_model == "claude-opus-4-8"
    assert s.database_url.startswith("postgresql+psycopg://")
    assert s.staleness_warn_months == 12


def test_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VCM_EXTRACT_MODEL", "claude-opus-4-8")
    get_settings.cache_clear()
    try:
        assert get_settings().extract_model == "claude-opus-4-8"
    finally:
        get_settings.cache_clear()
