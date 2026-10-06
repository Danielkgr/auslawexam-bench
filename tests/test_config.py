"""Tests for the config-driven model registry."""

from __future__ import annotations

from auslex.config import (
    DEFAULT_LOCAL_BASE_URL,
    default_models,
    is_real,
    load_models,
    resolve_api_key,
)


def test_default_roster_has_eight_slots():
    """The default roster contains exactly the eight canonical slots."""
    names = {s.name for s in default_models()}
    assert names == {"gpt", "claude", "gemini", "groq", "deepseek", "mistral", "qwen", "local"}


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


def test_is_real_local_needs_base_url_and_model(monkeypatch):
    monkeypatch.delenv("AUSLEX_LOCAL_MODEL", raising=False)
    local = next(s for s in load_models() if s.name == "local")
    assert is_real(local) is False  # no model named: never guess one
    monkeypatch.setenv("AUSLEX_LOCAL_MODEL", "my-model")
    local = next(s for s in load_models() if s.name == "local")
    assert is_real(local) is True


def test_is_real_commercial_needs_api_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    specs = load_models()
    gpt = next(s for s in specs if s.name == "gpt")
    assert is_real(gpt) is False
    assert resolve_api_key(gpt) is None

    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    assert is_real(gpt) is True


def test_config_file_override_applies(tmp_path, monkeypatch):
    import json

    p = tmp_path / "cfg.json"
    p.write_text(json.dumps({"models": {"gpt": {"model": "gpt-test", "max_tokens": 1234}}}))
    gpt = next(s for s in load_models(p) if s.name == "gpt")
    assert gpt.model == "gpt-test" and gpt.max_tokens == 1234


def test_config_file_rejects_unknown_settings(tmp_path):
    import json

    import pytest

    p = tmp_path / "cfg.json"
    p.write_text(json.dumps({"models": {"gpt": {"modle": "typo"}}}))
    with pytest.raises(ValueError, match="modle"):
        load_models(p)


def test_environment_wins_over_config_for_the_local_slot(tmp_path, monkeypatch):
    import json

    p = tmp_path / "cfg.json"
    p.write_text(json.dumps({"models": {"local": {"model": "from-config"}}}))
    monkeypatch.delenv("AUSLEX_LOCAL_MODEL", raising=False)
    assert next(s for s in load_models(p) if s.name == "local").model == "from-config"
    monkeypatch.setenv("AUSLEX_LOCAL_MODEL", "from-env")
    assert next(s for s in load_models(p) if s.name == "local").model == "from-env"
