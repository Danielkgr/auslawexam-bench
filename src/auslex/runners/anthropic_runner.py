"""Claude runner on the official Anthropic Python SDK.

The request carries no sampling parameters.  Current Claude models such as
``claude-opus-5-5`` reject ``temperature``, ``top_p`` and ``top_k`` with HTTP
400, so the Claude slot runs at the model's own sampling and the benchmark's
repetitions measure the run-to-run variance instead.  Thinking cannot be turned
off on Opus 5.5, so depth is set explicitly through ``output_config.effort``.

The answer is streamed, because an essay answer plus adaptive thinking can need
far more output tokens than a non-streaming request can safely wait for.

The SDK is an optional dependency: ``pip install "auslex[claude]"``.
"""

from __future__ import annotations

import os
import time
from typing import Any, Optional

from ..config import ModelSpec
from .base import RawResponse, Runner, estimate_cost_usd

# Standard first-party prices in USD per million tokens, input then output.
PRICES_PER_MTOK: dict[str, tuple[float, float]] = {
    "claude-opus-5-5": (4.0, 20.0),
    "claude-sonnet-5-5": (2.0, 10.0),
    "claude-haiku-4-5": (1.0, 5.0),
    "claude-fable-5-1": (10.0, 50.0),
}

# Exam answers are intelligence-sensitive work, so the default is "high".  A
# slot can override it with ``extra={"effort": ...}``.
DEFAULT_EFFORT = "high"


def _require_sdk() -> Any:
    try:
        import anthropic
    except ImportError as exc:  # pragma: no cover - exercised only without the extra
        raise RuntimeError(
            'the Claude slot needs the Anthropic SDK: pip install "auslex[claude]"'
        ) from exc
    return anthropic


class AnthropicRunner(Runner):
    """Send one exam question to Claude and record exactly what came back."""

    def __init__(self, spec: ModelSpec, *, client: Any = None, timeout: float = 900.0):
        super().__init__(spec)
        self._sdk = _require_sdk()
        if client is None:
            key = os.environ.get(spec.api_key_env or "")
            if not key:
                raise RuntimeError(
                    f"no API key for {spec.name!r}: set {spec.api_key_env} to run live"
                )
            client = self._sdk.Anthropic(
                api_key=key, timeout=timeout, base_url=spec.base_url or None
            )
        self._client = client

    def _params(self, messages: list[dict[str, str]]) -> dict[str, Any]:
        system = "\n\n".join(m["content"] for m in messages if m.get("role") == "system")
        turns = [
            {"role": m["role"], "content": m["content"]}
            for m in messages
            if m.get("role") != "system"
        ]
        # Deliberately absent: temperature, top_p and top_k, which current
        # models reject.  Also deliberately absent: server-side fallbacks.  A
        # fallback would answer a refused request with a different model, which
        # would silently change the model under test.  A refusal is recorded as
        # its own outcome instead.
        return {
            "model": self.spec.model,
            "max_tokens": self.spec.max_tokens,
            "system": system,
            "messages": turns,
            "output_config": {"effort": self.spec.extra.get("effort", DEFAULT_EFFORT)},
        }

    def complete(
        self,
        messages: list[dict[str, str]],
        *,
        seed: Optional[int] = None,  # Claude has no seed parameter; recorded only
        item: Optional[dict[str, Any]] = None,
    ) -> RawResponse:
        sdk = self._sdk
        t0 = time.perf_counter()
        try:
            with self._client.messages.stream(**self._params(messages)) as stream:
                message = stream.get_final_message()
        except sdk.RateLimitError as exc:
            return self._failed(f"rate limited (HTTP 429): {exc.message}", t0)
        except sdk.APIStatusError as exc:
            return self._failed(f"HTTP {exc.status_code}: {exc.message}", t0)
        except sdk.APIConnectionError as exc:
            return self._failed(f"connection error: {exc}", t0)
        latency_ms = int((time.perf_counter() - t0) * 1000)

        text = "".join(b.text for b in message.content if b.type == "text")
        pt = int(message.usage.input_tokens or 0)
        ct = int(message.usage.output_tokens or 0)
        price = PRICES_PER_MTOK.get(self.spec.model)
        cost = round(estimate_cost_usd(pt, ct, *price), 6) if price else None

        error: Optional[str] = None
        if message.stop_reason == "refusal":
            # stop_details is populated only for a refusal, so read it only here.
            details = message.stop_details
            category = getattr(details, "category", None) if details else None
            error = f"refusal: the model declined to answer (category={category})"
        elif message.stop_reason == "max_tokens":
            error = f"truncated: the answer hit max_tokens={self.spec.max_tokens}"

        return RawResponse(
            text=text,
            finish_reason=message.stop_reason or "",
            prompt_tokens=pt,
            completion_tokens=ct,
            latency_ms=latency_ms,
            cost_usd=cost,
            model=message.model,
            is_mock=False,
            error=error,
            raw=message.to_dict(),
        )

    def _failed(self, error: str, t0: float) -> RawResponse:
        return RawResponse(
            text="",
            error=error,
            model=self.spec.model,
            latency_ms=int((time.perf_counter() - t0) * 1000),
        )
