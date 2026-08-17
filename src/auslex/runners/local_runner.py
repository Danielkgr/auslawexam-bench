"""Open-weight model via any OpenAI-compatible endpoint (llama.cpp / vLLM /
llama-swap / Ollama). This is the runner used for the benchmark's open-weight
slot — pinned to an exact model id (and, where the server exposes it, the exact
GGUF path in the raw payload), so runs are reproducible.
"""

from __future__ import annotations

from typing import Any, Optional

from ..config import ModelSpec
from .base import Runner, RawResponse, http_json


class LocalRunner(Runner):
    def __init__(self, spec: ModelSpec, *, timeout: float = 900.0):
        super().__init__(spec)
        if not spec.base_url:
            raise ValueError(f"local runner for {spec.name!r} has no base_url")
        self._timeout = timeout
        self._url = spec.base_url.rstrip("/") + "/chat/completions"

    def complete(
        self,
        messages: list[dict[str, str]],
        *,
        seed: Optional[int] = None,
        item: Optional[dict] = None,  # noqa: ARG002  (ignored by real runners)
    ) -> RawResponse:
        payload: dict[str, Any] = {
            "model": self.spec.model,
            "messages": messages,
            "temperature": self.spec.temperature,
            "max_tokens": self.spec.max_tokens,
        }
        if seed is not None:
            # Some servers honour a top-level seed; harmless if ignored.
            payload["seed"] = seed
        # Pass through template knobs (e.g. Qwen3 "enable_thinking": false) so a
        # thinking model returns a direct answer in `content` instead of spending
        # its whole budget in `reasoning_content`. Non-Qwen servers ignore unknown
        # template kwargs, so this is safe to send always when configured.
        ctk = self.spec.extra.get("chat_template_kwargs")
        if ctk:
            payload["chat_template_kwargs"] = ctk

        try:
            body, latency_ms = self._timed(lambda: http_json(
                self._url, payload, headers={}, timeout=self._timeout
            ))
        except RuntimeError as e:
            return RawResponse(text="", error=str(e), model=self.spec.model)

        try:
            choice = body["choices"][0]
            msg = choice.get("message", {})
            usage = body.get("usage", {}) or {}
            text = msg.get("content") or ""
            reasoning = msg.get("reasoning_content")
            finish_reason = choice.get("finish_reason", "stop")
            # A thinking model that spent its whole budget in reasoning returns an
            # empty answer; surface that clearly so the transcript self-explains.
            error: Optional[str] = None
            if not text.strip() and (reasoning or "").strip():
                error = (
                    f"empty answer: model produced only reasoning_content "
                    f"(finish_reason={finish_reason}); disable thinking "
                    f"(AUSLEX_LOCAL_ENABLE_THINKING=0) or raise max_tokens"
                )
            return RawResponse(
                text=text,
                reasoning=reasoning,
                finish_reason=finish_reason,
                prompt_tokens=int(usage.get("prompt_tokens", 0)),
                completion_tokens=int(usage.get("completion_tokens", 0)),
                latency_ms=latency_ms,
                cost_usd=0.0,
                system_fingerprint=body.get("system_fingerprint"),
                model=body.get("model", self.spec.model),
                is_mock=False,
                error=error,
                raw=body,
            )
        except (KeyError, IndexError, TypeError) as e:
            return RawResponse(
                text="", error=f"unexpected local response shape: {e}",
                model=self.spec.model, raw=body,
            )
