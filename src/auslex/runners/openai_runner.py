"""OpenAI Chat Completions runner (real, stdlib-only).

Requires ``OPENAI_API_KEY`` (or a custom key via the spec). When no key is
present, the orchestrator substitutes the :class:`~auslex.runners.mock_runner.MockRunner`
— this runner is only constructed for live runs.
"""

from __future__ import annotations

import os
from typing import Any

from ..config import ModelSpec
from ..pricing import cost_usd
from .base import RawResponse, Runner, http_json

DEFAULT_BASE = "https://api.openai.com/v1"


class OpenAIRunner(Runner):
    def __init__(self, spec: ModelSpec, *, timeout: float = 600.0):
        super().__init__(spec)
        self._timeout = timeout
        self._base = (spec.base_url or DEFAULT_BASE).rstrip("/")
        self._url = self._base + "/chat/completions"
        self._key = self._resolve_key() or ""
        if not self._key:
            raise RuntimeError(
                f"no API key for {spec.name!r}: set {spec.api_key_env} to run "
                "live (otherwise the mock runner is used)"
            )

    def _resolve_key(self) -> str | None:
        return os.environ.get(self.spec.api_key_env or "")

    def _payload(self, messages: list[dict[str, str]], seed: int | None) -> dict[str, Any]:
        # GPT-5-family reasoning models reject max_tokens and any temperature
        # other than the default, so the token limit goes under the slot's
        # configured parameter name and temperature is sent only when the slot
        # sets one.  OpenAI-compatible providers that still expect max_tokens
        # keep the default name.
        payload: dict[str, Any] = {
            "model": self.spec.model,
            "messages": messages,
            self.spec.max_tokens_param: self.spec.max_tokens,
        }
        if self.spec.temperature is not None:
            payload["temperature"] = self.spec.temperature
        if seed is not None:
            payload["seed"] = seed
        return payload

    def complete(
        self, messages, *, seed: int | None = None, item: dict | None = None
    ) -> RawResponse:  # noqa: ARG002
        payload = self._payload(messages, seed)
        headers = {
            "Authorization": f"Bearer {self._key}",
            "Content-Type": "application/json",
        }
        try:
            body, latency_ms = self._timed(
                lambda: http_json(self._url, payload, headers, timeout=self._timeout)
            )
        except RuntimeError as e:
            return RawResponse(text="", error=str(e), model=self.spec.model)

        try:
            choice = body["choices"][0]
            msg = choice.get("message", {})
            usage = body.get("usage", {}) or {}
            pt = int(usage.get("prompt_tokens", 0))
            ct = int(usage.get("completion_tokens", 0))
            text = msg.get("content") or ""
            finish_reason = choice.get("finish_reason") or "stop"
            error: str | None = None
            if msg.get("refusal"):
                error = f"refusal: {msg['refusal']}"
            elif finish_reason == "content_filter":
                error = "refusal: the provider's content filter stopped the answer"
            elif finish_reason == "length":
                error = (
                    f"truncated: the answer hit {self.spec.max_tokens_param}={self.spec.max_tokens}"
                )
            return RawResponse(
                text=text,
                finish_reason=finish_reason,
                error=error,
                prompt_tokens=pt,
                completion_tokens=ct,
                latency_ms=latency_ms,
                cost_usd=cost_usd(self.spec.model, pt, ct),
                system_fingerprint=body.get("system_fingerprint"),
                model=body.get("model", self.spec.model),
                is_mock=False,
                raw=body,
            )
        except (KeyError, IndexError, TypeError) as e:
            return RawResponse(
                text="",
                error=f"unexpected OpenAI response shape: {e}",
                model=self.spec.model,
                raw=body,
            )
