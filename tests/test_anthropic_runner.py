"""The Claude runner against a mocked Messages API (no network, no key)."""

from __future__ import annotations

import json

import anthropic
import httpx2
import pytest
from conftest import make_item

from auslex.config import ModelSpec
from auslex.prompts import messages as build_messages
from auslex.runners.anthropic_runner import AnthropicRunner


def _spec(**over) -> ModelSpec:
    base = dict(
        name="claude",
        vendor="anthropic",
        model="claude-opus-5-5",
        runner="anthropic",
        api_key_env="ANTHROPIC_API_KEY",
        temperature=None,
        max_tokens=32000,
        extra={"effort": "high"},
    )
    base.update(over)
    return ModelSpec(**base)


def _sse(text: str, stop_reason: str, stop_details=None, out_tokens: int = 42) -> str:
    """A minimal Messages API event stream carrying one text block."""
    events = [
        (
            "message_start",
            {
                "type": "message_start",
                "message": {
                    "id": "msg_test",
                    "type": "message",
                    "role": "assistant",
                    "model": "claude-opus-5-5",
                    "content": [],
                    "stop_reason": None,
                    "stop_sequence": None,
                    "usage": {"input_tokens": 300, "output_tokens": 1},
                },
            },
        ),
        (
            "content_block_start",
            {
                "type": "content_block_start",
                "index": 0,
                "content_block": {"type": "text", "text": ""},
            },
        ),
        (
            "content_block_delta",
            {
                "type": "content_block_delta",
                "index": 0,
                "delta": {"type": "text_delta", "text": text},
            },
        ),
        ("content_block_stop", {"type": "content_block_stop", "index": 0}),
        (
            "message_delta",
            {
                "type": "message_delta",
                "delta": {
                    "stop_reason": stop_reason,
                    "stop_sequence": None,
                    "stop_details": stop_details,
                },
                "usage": {"output_tokens": out_tokens},
            },
        ),
        ("message_stop", {"type": "message_stop"}),
    ]
    return "".join(f"event: {name}\ndata: {json.dumps(data)}\n\n" for name, data in events)


def _runner(handler, seen: list | None = None) -> AnthropicRunner:
    def record(request: httpx2.Request) -> httpx2.Response:
        if seen is not None:
            seen.append(json.loads(request.content))
        return handler(request)

    client = anthropic.Anthropic(
        api_key="test",
        max_retries=0,
        http_client=httpx2.Client(transport=httpx2.MockTransport(record)),
    )
    return AnthropicRunner(_spec(), client=client)


def _stream(body: str) -> httpx2.Response:
    return httpx2.Response(200, text=body, headers={"content-type": "text/event-stream"})


def test_success_records_text_usage_cost_and_latency():
    seen: list[dict] = []
    runner = _runner(lambda r: _stream(_sse("The answer cites Kioa v West.", "end_turn")), seen)
    resp = runner.complete(build_messages(make_item()), seed=0)

    assert resp.ok and resp.text == "The answer cites Kioa v West."
    assert resp.finish_reason == "end_turn"
    assert (resp.prompt_tokens, resp.completion_tokens) == (300, 42)
    assert resp.cost_usd == pytest.approx((300 * 4 + 42 * 20) / 1_000_000)
    assert resp.latency_ms >= 0 and resp.model == "claude-opus-5-5"

    body = seen[0]
    assert body["model"] == "claude-opus-5-5" and body["stream"] is True
    assert body["output_config"] == {"effort": "high"}
    assert body["max_tokens"] == 32000
    assert body["system"].startswith("You are an experienced Australian lawyer")
    assert [m["role"] for m in body["messages"]] == ["user"]
    # Current Claude models reject sampling parameters, and a fallback would
    # change the model under test, so none of these may be sent.
    for absent in ("temperature", "top_p", "top_k", "random_seed", "fallbacks", "thinking"):
        assert absent not in body


def test_refusal_is_recorded_as_an_error_with_its_category():
    details = {"type": "refusal", "category": "cyber", "explanation": "declined"}
    runner = _runner(lambda r: _stream(_sse("", "refusal", stop_details=details)))
    resp = runner.complete(build_messages(make_item()))
    assert not resp.ok
    assert resp.finish_reason == "refusal"
    assert "refusal" in resp.error and "cyber" in resp.error


def test_truncation_is_recorded_as_an_error_but_keeps_the_text():
    runner = _runner(lambda r: _stream(_sse("A partial answer", "max_tokens")))
    resp = runner.complete(build_messages(make_item()))
    assert not resp.ok
    assert resp.text == "A partial answer"
    assert "max_tokens" in resp.error


@pytest.mark.parametrize(
    ("status", "expected"),
    [(429, "rate limited"), (400, "HTTP 400"), (529, "HTTP 529")],
)
def test_http_errors_are_recorded_not_raised(status, expected):
    def handler(request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(
            status, json={"type": "error", "error": {"type": "api_error", "message": "nope"}}
        )

    resp = _runner(handler).complete(build_messages(make_item()))
    assert not resp.ok and expected in resp.error and resp.text == ""


def test_connection_failure_is_recorded_not_raised():
    def handler(request: httpx2.Request) -> httpx2.Response:
        raise httpx2.ConnectError("no route to host", request=request)

    resp = _runner(handler).complete(build_messages(make_item()))
    assert not resp.ok and resp.error.startswith("connection error")


def test_missing_key_is_a_clear_error(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
        AnthropicRunner(_spec())
