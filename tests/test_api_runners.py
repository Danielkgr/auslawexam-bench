"""The OpenAI-compatible, Gemini, and local runners against mocked HTTP.

Each runner posts through a module-level ``http_json`` helper, which is patched
here, so no test touches the network or needs a key.
"""

from __future__ import annotations

import pytest
from conftest import make_item

from auslex.config import ModelSpec, default_models
from auslex.prompts import messages as build_messages
from auslex.runners import google_runner, local_runner, openai_runner

MSGS = build_messages(make_item())


def _slot(name: str, **over) -> ModelSpec:
    import dataclasses

    spec = next(s for s in default_models() if s.name == name)
    return dataclasses.replace(spec, **over)


class _FakeHTTP:
    """Stands in for http_json: records the payload, returns or raises."""

    def __init__(self, body=None, error: str | None = None):
        self.body, self.error, self.calls = body, error, []

    def __call__(self, url, payload, headers, timeout=600.0):
        self.calls.append({"url": url, "payload": payload, "headers": headers})
        if self.error:
            raise RuntimeError(self.error)
        return self.body


def _chat(content="An answer.", finish="stop", refusal=None):
    return {
        "model": "gpt-5.6",
        "system_fingerprint": "fp_test",
        "choices": [
            {
                "finish_reason": finish,
                "message": {"role": "assistant", "content": content, "refusal": refusal},
            }
        ],
        "usage": {"prompt_tokens": 280, "completion_tokens": 40},
    }


# --- OpenAI-compatible ------------------------------------------------------ #


@pytest.fixture
def openai_key(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")


def test_openai_success_uses_max_completion_tokens_and_no_temperature(monkeypatch, openai_key):
    fake = _FakeHTTP(_chat())
    monkeypatch.setattr(openai_runner, "http_json", fake)
    resp = openai_runner.OpenAIRunner(_slot("gpt")).complete(MSGS, seed=3)

    assert resp.ok and resp.text == "An answer."
    assert (resp.prompt_tokens, resp.completion_tokens) == (280, 40)
    assert resp.system_fingerprint == "fp_test"
    payload = fake.calls[0]["payload"]
    assert payload["max_completion_tokens"] == 16000
    assert "max_tokens" not in payload
    assert "temperature" not in payload
    assert payload["seed"] == 3
    assert fake.calls[0]["headers"]["Authorization"] == "Bearer sk-test"


def test_openai_compatible_slot_keeps_max_tokens_and_its_temperature(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test")
    fake = _FakeHTTP(_chat())
    monkeypatch.setattr(openai_runner, "http_json", fake)
    openai_runner.OpenAIRunner(_slot("deepseek")).complete(MSGS)
    payload = fake.calls[0]["payload"]
    assert payload["max_tokens"] == 3000 and payload["temperature"] == 0.0


def test_openai_refusal_is_an_error(monkeypatch, openai_key):
    monkeypatch.setattr(openai_runner, "http_json", _FakeHTTP(_chat(None, refusal="I can't help")))
    resp = openai_runner.OpenAIRunner(_slot("gpt")).complete(MSGS)
    assert not resp.ok and resp.error.startswith("refusal")


def test_openai_truncation_is_an_error_but_keeps_the_text(monkeypatch, openai_key):
    monkeypatch.setattr(openai_runner, "http_json", _FakeHTTP(_chat("Partial", "length")))
    resp = openai_runner.OpenAIRunner(_slot("gpt")).complete(MSGS)
    assert not resp.ok and resp.text == "Partial" and "max_completion_tokens" in resp.error


def test_openai_http_error_is_recorded(monkeypatch, openai_key):
    monkeypatch.setattr(openai_runner, "http_json", _FakeHTTP(error="HTTP 400 from x: bad"))
    resp = openai_runner.OpenAIRunner(_slot("gpt")).complete(MSGS)
    assert not resp.ok and "HTTP 400" in resp.error


# --- Gemini ----------------------------------------------------------------- #


@pytest.fixture
def google_key(monkeypatch):
    monkeypatch.setenv("GOOGLE_API_KEY", "g-test")


def _gemini(text="An answer.", finish="STOP"):
    return {
        "candidates": [{"finishReason": finish, "content": {"parts": [{"text": text}]}}],
        "usageMetadata": {"promptTokenCount": 250, "candidatesTokenCount": 30},
    }


def test_gemini_success(monkeypatch, google_key):
    fake = _FakeHTTP(_gemini())
    monkeypatch.setattr(google_runner, "http_json", fake)
    resp = google_runner.GoogleRunner(_slot("gemini")).complete(MSGS, seed=1)
    assert resp.ok and resp.text == "An answer."
    assert (resp.prompt_tokens, resp.completion_tokens) == (250, 30)
    call = fake.calls[0]
    assert call["headers"]["x-goog-api-key"] == "g-test"
    assert call["payload"]["systemInstruction"]["parts"][0]["text"].startswith("You are")
    assert call["payload"]["generationConfig"]["seed"] == 1


def test_gemini_safety_stop_is_a_refusal(monkeypatch, google_key):
    monkeypatch.setattr(google_runner, "http_json", _FakeHTTP(_gemini("", "SAFETY")))
    resp = google_runner.GoogleRunner(_slot("gemini")).complete(MSGS)
    assert not resp.ok and resp.error.startswith("refusal")


def test_gemini_blocked_prompt_is_a_refusal(monkeypatch, google_key):
    body = {"promptFeedback": {"blockReason": "SAFETY"}}
    monkeypatch.setattr(google_runner, "http_json", _FakeHTTP(body))
    resp = google_runner.GoogleRunner(_slot("gemini")).complete(MSGS)
    assert not resp.ok and "blocked" in resp.error


def test_gemini_truncation_is_an_error(monkeypatch, google_key):
    monkeypatch.setattr(google_runner, "http_json", _FakeHTTP(_gemini("Partial", "MAX_TOKENS")))
    resp = google_runner.GoogleRunner(_slot("gemini")).complete(MSGS)
    assert not resp.ok and resp.text == "Partial" and "maxOutputTokens" in resp.error


def test_gemini_http_error_is_recorded(monkeypatch, google_key):
    monkeypatch.setattr(google_runner, "http_json", _FakeHTTP(error="HTTP 503 from x: busy"))
    resp = google_runner.GoogleRunner(_slot("gemini")).complete(MSGS)
    assert not resp.ok and "HTTP 503" in resp.error


# --- Local OpenAI-compatible endpoint --------------------------------------- #


def test_local_success_sends_template_kwargs(monkeypatch):
    fake = _FakeHTTP(_chat())
    monkeypatch.setattr(local_runner, "http_json", fake)
    resp = local_runner.LocalRunner(_slot("local")).complete(MSGS)
    assert resp.ok and resp.cost_usd == 0.0
    assert "chat_template_kwargs" in fake.calls[0]["payload"]


def test_local_truncation_is_an_error(monkeypatch):
    monkeypatch.setattr(local_runner, "http_json", _FakeHTTP(_chat("Partial", "length")))
    resp = local_runner.LocalRunner(_slot("local")).complete(MSGS)
    assert not resp.ok and "max_tokens" in resp.error


def test_local_reasoning_only_answer_is_an_error(monkeypatch):
    body = _chat("")
    body["choices"][0]["message"]["reasoning_content"] = "thinking..."
    monkeypatch.setattr(local_runner, "http_json", _FakeHTTP(body))
    resp = local_runner.LocalRunner(_slot("local")).complete(MSGS)
    assert not resp.ok and "reasoning_content" in resp.error


def test_local_http_error_is_recorded(monkeypatch):
    monkeypatch.setattr(local_runner, "http_json", _FakeHTTP(error="URL error contacting x"))
    resp = local_runner.LocalRunner(_slot("local")).complete(MSGS)
    assert not resp.ok and "URL error" in resp.error
