"""Tests for the config-driven model registry."""

from __future__ import annotations

from auslex.config import (
    DEFAULT_LOCAL_BASE_URL,
    default_models,
    is_real,
    load_models,
    resolve_api_key,
)


def test_default_roster_has_four_slots():
    names = {s.name for s in default_models()}
    assert names == {"gpt", "claude", "gemini", "local"}


def test_local_thinking_is_off_by_default(monkeypatch):
    monkeypatch.delenv("AUSLEX_LOCAL_ENABLE_THINKING", raising=False)
    local = next(s for s in default_models() if s.name == "local")
    assert local.extra["chat_template_kwargs"]["enable_thinking"] is False


def test_local_thinking_env_override(monkeypatch):
    monkeypatch.setenv("AUSLEX_LOCAL_ENABLE_THINKING", "1")
    local = next(s for s in default_models() if s.name == "local")
    assert local.extra["chat_template_kwargs"]["enable_thinking"] is True


def test_local_base_url_env_override(monkeypatch):
    monkeypatch.setenv("AUSLEX_LOCAL_BASE_URL", "http://127.0.0.1:9999/v1")
    specs = load_models()
    local = next(s for s in specs if s.name == "local")
    assert local.base_url == "http://127.0.0.1:9999/v1"


def test_default_local_base_url(monkeypatch):
    monkeypatch.delenv("AUSLEX_LOCAL_BASE_URL", raising=False)
    specs = load_models()
    local = next(s for s in specs if s.name == "local")
    assert local.base_url == DEFAULT_LOCAL_BASE_URL


def test_is_real_local_needs_base_url():
    specs = load_models()
    local = next(s for s in specs if s.name == "local")
    assert is_real(local) is True


def test_is_real_commercial_needs_api_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    specs = load_models()
    gpt = next(s for s in specs if s.name == "gpt")
    assert is_real(gpt) is False
    assert resolve_api_key(gpt) is None

    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    assert is_real(gpt) is True
