"""Runner contract + shared HTTP helper.

A ``Runner`` turns a prompt (OpenAI-style message list) into a ``RawResponse`` —
the exact, auditable record of what the model returned, including tokens, cost,
latency, and the provider system fingerprint. Every runner in the benchmark
implements the same ``complete`` signature so the orchestrator is runner-agnostic.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional

from ..config import ModelSpec


@dataclass
class RawResponse:
    """One model call's auditable output."""

    text: str
    reasoning: Optional[str] = None
    finish_reason: str = "stop"
    prompt_tokens: int = 0
    completion_tokens: int = 0
    latency_ms: int = 0
    cost_usd: Optional[float] = None
    system_fingerprint: Optional[str] = None
    model: Optional[str] = None
    is_mock: bool = False
    error: Optional[str] = None
    raw: Optional[dict[str, Any]] = field(default=None, repr=False)

    @property
    def ok(self) -> bool:
        return self.error is None

    def to_dict(self) -> dict[str, Any]:
        d = {
            "text": self.text,
            "reasoning": self.reasoning,
            "finish_reason": self.finish_reason,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "latency_ms": self.latency_ms,
            "cost_usd": self.cost_usd,
            "system_fingerprint": self.system_fingerprint,
            "model": self.model,
            "is_mock": self.is_mock,
            "error": self.error,
        }
        return d


def http_json(
    url: str,
    payload: dict[str, Any],
    headers: dict[str, str],
    timeout: float = 600.0,
) -> dict[str, Any]:
    """POST ``payload`` as JSON, return the parsed JSON body.

    Raises ``RuntimeError`` with the status + body on HTTP error.
    """
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    for k, v in headers.items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {e.code} from {url}: {detail[:500]}") from None
    except urllib.error.URLError as e:
        raise RuntimeError(f"URL error contacting {url}: {e.reason}") from None
    return json.loads(body)


def estimate_cost_usd(
    prompt_tokens: int,
    completion_tokens: int,
    in_per_mtok: float,
    out_per_mtok: float,
) -> float:
    """Rough USD cost from token counts and per-million-token prices."""
    return (
        prompt_tokens * in_per_mtok + completion_tokens * out_per_mtok
    ) / 1_000_000


class Runner(ABC):
    """Base class for all model runners."""

    def __init__(self, spec: ModelSpec):
        self.spec = spec

    @abstractmethod
    def complete(
        self,
        messages: list[dict[str, str]],
        *,
        seed: Optional[int] = None,
        item: Optional[dict] = None,
    ) -> RawResponse:
        """Send one completion.

        ``seed`` is for reproducible mock runs; ``item`` is the source item and
        is used by the mock runner to synthesise a plausible answer (real
        runners ignore it).
        """
        raise NotImplementedError

    def _timed(self, fn):
        t0 = time.perf_counter()
        out = fn()
        return out, int((time.perf_counter() - t0) * 1000)
