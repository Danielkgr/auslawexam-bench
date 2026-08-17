"""Google Gemini (Generative Language API) runner (real, stdlib-only).

Gemini takes the system prompt via ``systemInstruction`` and contents as a list
of ``{role, parts}``. The API key is passed in the ``x-goog-api-key`` header.
When no key is present the orchestrator substitutes the mock runner.
"""

from __future__ import annotations

import os
from typing import Any, Optional

from ..config import ModelSpec
from .base import Runner, RawResponse, estimate_cost_usd, http_json

# Illustrative per-1M-token USD prices (Pro-class). Update before a live run.
_IN_PER_MTOK = 1.25
_OUT_PER_MTOK = 5.0

DEFAULT_BASE = "https://generativelanguage.googleapis.com/v1beta"


class GoogleRunner(Runner):
    def __init__(self, spec: ModelSpec, *, timeout: float = 600.0):
        super().__init__(spec)
        self._timeout = timeout
        self._base = (spec.base_url or DEFAULT_BASE).rstrip("/")
        self._url = f"{self._base}/models/{self.spec.model}:generateContent"
        self._key = os.environ.get(self.spec.api_key_env or "")
        if not self._key:
            raise RuntimeError(
                f"no API key for {spec.name!r}: set {spec.api_key_env} to run "
                "live (otherwise the mock runner is used)"
            )

    def _build(self, messages: list[dict[str, str]], *, seed: Optional[int] = None) -> dict[str, Any]:
        system_parts = [m["content"] for m in messages if m.get("role") == "system"]
        contents = [
            {"role": "user" if m.get("role") == "user" else "model",
             "parts": [{"text": m["content"]}]}
            for m in messages if m.get("role") in ("user", "assistant")
        ]
        payload: dict[str, Any] = {
            "contents": contents,
            "generationConfig": {
                "temperature": self.spec.temperature,
                "maxOutputTokens": self.spec.max_tokens,
            },
        }
        if seed is not None:
            payload["generationConfig"]["seed"] = seed
        if system_parts:
            payload["systemInstruction"] = {"parts": [{"text": "\n\n".join(system_parts)}]}
        return payload

    def complete(
        self, messages, *, seed: Optional[int] = None, item: Optional[dict] = None
    ) -> RawResponse:  # noqa: ARG002
        payload = self._build(messages, seed=seed)
        headers = {"x-goog-api-key": self._key, "Content-Type": "application/json"}
        try:
            body, latency_ms = self._timed(lambda: http_json(
                self._url, payload, headers, timeout=self._timeout
            ))
        except RuntimeError as e:
            return RawResponse(text="", error=str(e), model=self.spec.model)

        try:
            cand = body["candidates"][0]
            parts = cand.get("content", {}).get("parts", [])
            text = "".join(p.get("text", "") for p in parts)
            usage = body.get("usageMetadata", {}) or {}
            pt = int(usage.get("promptTokenCount", 0))
            ct = int(usage.get("candidatesTokenCount", 0))
            return RawResponse(
                text=text,
                finish_reason=cand.get("finishReason", "STOP"),
                prompt_tokens=pt,
                completion_tokens=ct,
                latency_ms=latency_ms,
                cost_usd=round(estimate_cost_usd(pt, ct, _IN_PER_MTOK, _OUT_PER_MTOK), 6),
                model=self.spec.model,
                is_mock=False,
                raw=body,
            )
        except (KeyError, IndexError, TypeError) as e:
            return RawResponse(
                text="", error=f"unexpected Gemini response shape: {e}",
                model=self.spec.model, raw=body,
            )
