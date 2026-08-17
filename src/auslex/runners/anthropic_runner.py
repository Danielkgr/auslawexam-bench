"""Anthropic Messages API runner (real, stdlib-only).

The Anthropic API takes the system prompt as a top-level ``system`` field (not
in ``messages``) and requires ``max_tokens``. When no key is present the
orchestrator substitutes the mock runner.
"""

from __future__ import annotations

import os
from typing import Any, Optional

from ..config import ModelSpec
from .base import Runner, RawResponse, estimate_cost_usd, http_json

# Illustrative per-1M-token USD prices (Opus-class). Update before a live run.
_IN_PER_MTOK = 15.0
_OUT_PER_MTOK = 75.0

DEFAULT_BASE = "https://api.anthropic.com/v1"


class AnthropicRunner(Runner):
    def __init__(self, spec: ModelSpec, *, timeout: float = 600.0):
        super().__init__(spec)
        self._timeout = timeout
        self._base = (spec.base_url or DEFAULT_BASE).rstrip("/")
        self._url = self._base + "/messages"
        self._key = os.environ.get(self.spec.api_key_env or "")
        if not self._key:
            raise RuntimeError(
                f"no API key for {spec.name!r}: set {spec.api_key_env} to run "
                "live (otherwise the mock runner is used)"
            )

    def _split(self, messages: list[dict[str, str]]):
        system_parts = [m["content"] for m in messages if m.get("role") == "system"]
        rest = [m for m in messages if m.get("role") != "system"]
        return "\n\n".join(system_parts), rest

    def complete(
        self, messages, *, seed: Optional[int] = None, item: Optional[dict] = None
    ) -> RawResponse:  # noqa: ARG002
        system, msgs = self._split(messages)
        payload: dict[str, Any] = {
            "model": self.spec.model,
            "system": system,
            "messages": msgs,
            "temperature": self.spec.temperature,
            "max_tokens": self.spec.max_tokens,
        }
        if seed is not None:
            payload["random_seed"] = seed
        headers = {
            "x-api-key": self._key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }
        try:
            body, latency_ms = self._timed(lambda: http_json(
                self._url, payload, headers, timeout=self._timeout
            ))
        except RuntimeError as e:
            return RawResponse(text="", error=str(e), model=self.spec.model)

        try:
            blocks = body.get("content", [])
            text = "".join(b.get("text", "") for b in blocks if b.get("type") == "text")
            usage = body.get("usage", {}) or {}
            pt = int(usage.get("input_tokens", 0))
            ct = int(usage.get("output_tokens", 0))
            return RawResponse(
                text=text,
                finish_reason=body.get("stop_reason", "stop"),
                prompt_tokens=pt,
                completion_tokens=ct,
                latency_ms=latency_ms,
                cost_usd=round(estimate_cost_usd(pt, ct, _IN_PER_MTOK, _OUT_PER_MTOK), 6),
                model=body.get("model", self.spec.model),
                is_mock=False,
                raw=body,
            )
        except (KeyError, IndexError, TypeError) as e:
            return RawResponse(
                text="", error=f"unexpected Anthropic response shape: {e}",
                model=self.spec.model, raw=body,
            )
