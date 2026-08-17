"""Model runners + the config-driven factory.

``get_runner(spec)`` returns the right runner for a model slot:

- ``local``   -> :class:`LocalRunner` (real, OpenAI-compatible endpoint)
- ``openai``  -> :class:`OpenAIRunner`   (needs ``OPENAI_API_KEY``)
- ``anthropic`` -> :class:`AnthropicRunner` (needs ``ANTHROPIC_API_KEY``)
- ``google``  -> :class:`GoogleRunner`    (needs ``GOOGLE_API_KEY``)
- ``mock``    -> :class:`MockRunner` (always)

Commercial slots with no configured API key fall back to :class:`MockRunner`
(when ``allow_mock_fallback``), so the pipeline runs end-to-end offline and the
fallback is flagged ``is_mock`` on every record.
"""

from __future__ import annotations

from typing import Optional

from ..config import ModelSpec, is_real
from .anthropic_runner import AnthropicRunner
from .base import RawResponse, Runner, estimate_cost_usd, http_json
from .google_runner import GoogleRunner
from .local_runner import LocalRunner
from .mock_runner import MockRunner
from .openai_runner import OpenAIRunner

_API_RUNNERS = {
    "openai": OpenAIRunner,
    "anthropic": AnthropicRunner,
    "google": GoogleRunner,
}


def get_runner(spec: ModelSpec, *, allow_mock_fallback: bool = True) -> Runner:
    kind = spec.runner
    if kind == "mock":
        return MockRunner(spec)
    if kind == "local":
        if spec.base_url:
            return LocalRunner(spec)
        if allow_mock_fallback:
            return MockRunner(spec)
        raise RuntimeError(f"local runner {spec.name!r} has no base_url")
    if kind in _API_RUNNERS:
        if is_real(spec):
            return _API_RUNNERS[kind](spec)
        if allow_mock_fallback:
            return MockRunner(spec)
        raise RuntimeError(f"no API key for {spec.name!r}; set {spec.api_key_env}")
    raise ValueError(f"unknown runner kind {kind!r}")


def is_mock_runner(runner: Runner) -> bool:
    return isinstance(runner, MockRunner)


__all__ = [
    "Runner",
    "RawResponse",
    "http_json",
    "estimate_cost_usd",
    "MockRunner",
    "LocalRunner",
    "OpenAIRunner",
    "AnthropicRunner",
    "GoogleRunner",
    "get_runner",
    "is_mock_runner",
]
