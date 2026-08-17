"""OpenAI Chat Completions runner (real, stdlib-only).

Requires ``OPENAI_API_KEY`` (or a custom key via the spec). When no key is
present, the orchestrator substitutes the :class:`~auslex.runners.mock_runner.MockRunner`
— this runner is only constructed for live runs.
"""

from __future__ import annotations

import os
from typing import Any, Optional

from ..config import ModelSpec
from .base import Runner, RawResponse, estimate_cost_usd, http_json

# Illustrative per-1M-token USD prices. Update before any live run; cost is only
# computed when a key is present (never in the offline demo).
_IN_PER_MTOK = 2.5
_OUT_PER_MTOK = 10.0

DEFAULT_BASE = "https://api.openai.com/v1"


class OpenAIRunner(Runner):
    def __init__(self, spec: ModelSpec, *, timeout: float = 600.0):
        super().__init__(spec)
        self._timeout = timeout
        self._base = (spec.base_url or DEFAULT_BASE).rstrip("/")
        self._url = self._base + "/chat/completions"
        self._key = self._resolve_key()
        if not self._key:
            raise RuntimeError(
                f"no API key for {spec.name!r}: set {spec.api_key_env} to run "
                "live (otherwise the mock runner is used)"
            )

    def _resolve_key(self) -> Optional[str]:
        return os.environ.get(self.spec.api_key_env or "")

    def complete(
        self, messages, *, seed: Optional[int] = None, item: Optional[dict] = None
    ) -> RawResponse:  # noqa: ARG002
        payload: dict[str, Any] = {
            "model": self.spec.model,
            "messages": messages,
            "temperature": self.spec.temperature,
            "max_tokens": self.spec.max_tokens,
        }
        if seed is not None:
            payload["seed"] = seed
        headers = {
            "Authorization": f"Bearer {self._key}",
            "Content-Type": "application/json",
        }
        try:
            body, latency_ms = self._timed(lambda: http_json(
                self._url, payload, headers, timeout=self._timeout
            ))
        except RuntimeError as e:
            return RawResponse(text="", error=str(e), model=self.spec.model)

        try:
            choice = body["choices"][0]
            msg = choice.get("message", {})
            usage = body.get("usage", {}) or {}
            pt = int(usage.get("prompt_tokens", 0))
            ct = int(usage.get("completion_tokens", 0))
            text = msg.get("content") or ""
            return RawResponse(
                text=text,
                finish_reason=choice.get("finish_reason", "stop"),
                prompt_tokens=pt,
                completion_tokens=ct,
                latency_ms=latency_ms,
                cost_usd=round(estimate_cost_usd(pt, ct, _IN_PER_MTOK, _OUT_PER_MTOK), 6),
                system_fingerprint=body.get("system_fingerprint"),
                model=body.get("model", self.spec.model),
                is_mock=False,
                raw=body,
            )
        except (KeyError, IndexError, TypeError) as e:
            return RawResponse(
                text="", error=f"unexpected OpenAI response shape: {e}",
                model=self.spec.model, raw=body,
            )
