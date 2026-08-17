"""Config-driven model registry.

The four benchmark models are plain data here, so swapping in a new release (or
a different open-weight model) is a one-line change to this table — no code
touching the runners.

Resolution order for each field: default < config-file < environment.

Environment variables:
    OPENAI_API_KEY / ANTHROPIC_API_KEY / GOOGLE_API_KEY  — commercial slots
    AUSLEX_LOCAL_BASE_URL   (default http://localhost:10000/v1)
    AUSLEX_LOCAL_MODEL      (default: the loaded open-weight model)
"""

from __future__ import annotations

import dataclasses
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

# Discovered on this machine (llama.cpp / llama-swap, OpenAI-compatible).
DEFAULT_LOCAL_BASE_URL = "http://localhost:10000/v1"
DEFAULT_LOCAL_MODEL = "14. Qwen3.8-27B (Q5_K_M)"


def _local_enable_thinking() -> bool:
    """Whether the local slot runs in the model's chain-of-thought mode.

    Off by default: the benchmark scores the model's *answer*, and for
    thinking models (e.g. Qwen3) leaving thinking on would spend the whole
    token budget in ``reasoning_content`` and return an empty answer. Set
    ``AUSLEX_LOCAL_ENABLE_THINKING=1`` to opt a local model back in.
    """
    v = os.environ.get("AUSLEX_LOCAL_ENABLE_THINKING", "").strip().lower()
    return v in ("1", "true", "yes", "on")


@dataclass(frozen=True)
class ModelSpec:
    """One model slot in the benchmark."""

    name: str  # stable slot id, e.g. "gpt", "local"
    vendor: str  # "openai" | "anthropic" | "google" | "local"
    model: str  # API model id
    runner: str  # which runner implementation to use
    base_url: Optional[str] = None  # for local / OpenAI-compat endpoints
    api_key_env: Optional[str] = None
    temperature: float = 0.0
    max_tokens: int = 3000
    # Mock-only knobs: relative "competence" in [0,1] and fabrication tendency.
    mock_quality: float = 0.6
    mock_fabricate_rate: float = 0.15
    extra: dict[str, Any] = field(default_factory=dict)


def _env(name: Optional[str]) -> Optional[str]:
    if not name:
        return None
    val = os.environ.get(name)
    return val or None


def default_models() -> list[ModelSpec]:
    """The canonical eight-model benchmark roster (config-overridable).

    Commercial slots without an API key are skipped at runtime (set
    ``--mock`` to fall back to deterministic mocks for offline testing).
    """
    return [
        ModelSpec(
            name="gpt",
            vendor="openai",
            model="gpt-5.6",
            runner="openai",
            base_url="https://api.openai.com/v1",
            api_key_env="OPENAI_API_KEY",
            temperature=0.0,
            max_tokens=3000,
            mock_quality=0.86,
            mock_fabricate_rate=0.08,
        ),
        ModelSpec(
            name="claude",
            vendor="anthropic",
            model="claude-opus-5",
            runner="anthropic",
            api_key_env="ANTHROPIC_API_KEY",
            temperature=0.0,
            max_tokens=3000,
            mock_quality=0.83,
            mock_fabricate_rate=0.10,
        ),
        ModelSpec(
            name="gemini",
            vendor="google",
            model="gemini-2.0-flash",
            runner="google",
            api_key_env="GOOGLE_API_KEY",
            temperature=0.0,
            max_tokens=3000,
            mock_quality=0.80,
            mock_fabricate_rate=0.13,
        ),
        ModelSpec(
            name="groq",
            vendor="openai",
            model="llama-3.3-70b-specdec",
            runner="openai",
            base_url="https://api.groq.com/openai/v1",
            api_key_env="GROQ_API_KEY",
            temperature=0.0,
            max_tokens=3000,
            mock_quality=0.82,
            mock_fabricate_rate=0.10,
        ),
        ModelSpec(
            name="deepseek",
            vendor="openai",
            model="deepseek-chat",
            runner="openai",
            base_url="https://api.deepseek.com/v1",
            api_key_env="DEEPSEEK_API_KEY",
            temperature=0.0,
            max_tokens=3000,
            mock_quality=0.78,
            mock_fabricate_rate=0.12,
        ),
        ModelSpec(
            name="mistral",
            vendor="openai",
            model="mistral-small-latest",
            runner="openai",
            base_url="https://api.mistral.ai/v1",
            api_key_env="MISTRAL_API_KEY",
            temperature=0.0,
            max_tokens=3000,
            mock_quality=0.75,
            mock_fabricate_rate=0.14,
        ),
        ModelSpec(
            name="qwen",
            vendor="openai",
            model="qwen2.5-72b",
            runner="openai",
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            api_key_env="DASHSCOPE_API_KEY",
            temperature=0.0,
            max_tokens=3000,
            mock_quality=0.76,
            mock_fabricate_rate=0.13,
        ),
        ModelSpec(
            name="local",
            vendor="local",
            model=DEFAULT_LOCAL_MODEL,
            runner="local",
            base_url=os.environ.get("AUSLEX_LOCAL_BASE_URL", DEFAULT_LOCAL_BASE_URL),
            api_key_env=None,
            temperature=0.0,
            max_tokens=3000,
            mock_quality=0.55,
            mock_fabricate_rate=0.25,
            extra={"chat_template_kwargs": {"enable_thinking": _local_enable_thinking()}},
        ),
    ]


def _apply_overrides(specs: list[ModelSpec], cfg: dict[str, Any]) -> list[ModelSpec]:
    """Merge a config dict (from JSON) over the default specs, matched by name."""
    by_name = {s.name: s for s in specs}
    models_cfg = cfg.get("models", cfg)
    for name, overrides in models_cfg.items():
        if name not in by_name or not isinstance(overrides, dict):
            continue
        base = by_name[name]
        allowed = {f for f in dataclasses.fields(ModelSpec) if f != "extra"}
        kwargs = {k: v for k, v in overrides.items() if k in allowed}
        by_name[name] = dataclasses.replace(base, **kwargs)
    return list(by_name.values())


def load_models(cfg_path: Optional[str | Path] = None) -> list[ModelSpec]:
    """Build the model roster from defaults + optional config file + env."""
    specs = default_models()

    # Env overrides for the local slot (base_url / model).
    local = next((s for s in specs if s.vendor == "local"), None)
    if local is not None:
        env_url = os.environ.get("AUSLEX_LOCAL_BASE_URL", DEFAULT_LOCAL_BASE_URL)
        env_model = os.environ.get("AUSLEX_LOCAL_MODEL", DEFAULT_LOCAL_MODEL)
        specs = [
            dataclasses.replace(s, base_url=env_url, model=env_model)
            if s.name == local.name
            else s
            for s in specs
        ]

    if cfg_path:
        p = Path(cfg_path)
        if p.exists():
            import json

            with open(p, "r", encoding="utf-8") as fh:
                cfg = json.load(fh)
            specs = _apply_overrides(specs, cfg)

    return specs


def resolve_api_key(spec: ModelSpec) -> Optional[str]:
    """Return the API key for a spec if one is configured, else None."""
    return _env(spec.api_key_env)


def is_real(spec: ModelSpec) -> bool:
    """True if this spec can run for real (local endpoint or an API key present)."""
    if spec.vendor == "local":
        return bool(spec.base_url)
    return resolve_api_key(spec) is not None


def spec_dict(spec: ModelSpec) -> dict[str, Any]:
    return dataclasses.asdict(spec)
