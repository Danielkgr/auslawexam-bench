"""The run orchestrator.

``run(config)`` takes every item, sends the single shared prompt to every
configured model ``n_reps`` times (temperature 0, seed = rep), and writes an
append-only, content-hash-addressed transcript under ``runs/<run-id>/``.

Commercial slots with no API key (or a local endpoint that fails its probe)
are skipped by default — the pipeline no longer silently falls back to mock
output. Set ``allow_mock_fallback=True`` to restore the old behaviour for
offline testing.
"""

from __future__ import annotations

import datetime as dt
import platform
import sys
import urllib.request
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Optional

from .. import prompts as P
from ..config import ModelSpec, default_models, spec_dict
from ..io import hash_item
from ..runners import Runner, get_runner, is_mock_runner
from ..runners.local_runner import LocalRunner
from ..runners.mock_runner import MockRunner
from .storage import RunStore


def probe_local(base_url: str, timeout: float = 8.0) -> bool:
    """Cheap reachability check for a local OpenAI-compatible endpoint."""
    try:
        req = urllib.request.Request(base_url.rstrip("/") + "/models", method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status == 200
    except Exception:
        return False


def _utc_stamp() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d-%H%M%S")


@dataclass
class RunConfig:
    models: list[ModelSpec]
    items: list[dict[str, Any]]
    n_reps: int = 3
    run_id: Optional[str] = None
    out_root: Path = Path("runs")
    base_seed: int = 0
    allow_mock_fallback: bool = False
    question_filter: Optional[str] = None
    priestley_filter: Optional[str] = None
    jurisdiction_filter: Optional[str] = None
    difficulty_filter: Optional[str] = None


@dataclass
class ModelSummary:
    name: str
    is_mock: bool
    fallback: bool
    n_ok: int
    n_error: int


@dataclass
class RunReport:
    run_id: str
    run_dir: str
    n_models: int
    n_items: int
    n_reps: int
    n_completions: int
    n_ok: int
    n_error: int
    models: list[ModelSummary]
    started_at: str
    finished_at: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _make_meta(
    cfg: RunConfig,
    model_states: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "run_id": cfg.run_id,
        "started_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "prompt_template_version": P.TEMPLATE_VERSION,
        "n_reps": cfg.n_reps,
        "base_seed": cfg.base_seed,
        "models": model_states,
        "items": [
            {"id": it["id"], "version": it.get("version"),
             "content_hash": hash_item(it)}
            for it in cfg.items
        ],
        "python": platform.python_version(),
        "platform": platform.platform(),
        "sys_argv": sys.argv[:1],
    }


def run(cfg: RunConfig) -> RunReport:
    cfg.run_id = cfg.run_id or f"auslex-{_utc_stamp()}"
    store = RunStore(cfg.out_root, cfg.run_id)
    started = dt.datetime.now(dt.timezone.utc).isoformat()

    # Decide the runner per model, resolving any mock fallback up front so that
    # every row for a given model is homogeneous (never a real/mock mix).
    resolved: list[tuple[ModelSpec, Runner, bool, bool]] = []
    skipped: list[str] = []
    for spec in cfg.models:
        try:
            fallback = False
            runner = get_runner(spec, allow_mock_fallback=cfg.allow_mock_fallback)
            if isinstance(runner, LocalRunner) and not probe_local(spec.base_url or ""):
                if cfg.allow_mock_fallback:
                    fallback = True
                    runner = MockRunner(spec)
                else:
                    skipped.append(spec.name)
                    continue
            resolved.append((spec, runner, is_mock_runner(runner), fallback))
        except RuntimeError as exc:
            skipped.append(spec.name)
            print(f"  skip  {spec.name}: {exc}")

    # Meta is written once (config snapshot), before any completions, so a run
    # directory always self-describes even if it is interrupted.
    model_states = [
        {
            **spec_dict(spec),
            "runner": type(runner).__name__,
            "is_mock": is_mock,
            "fallback": fb,
        }
        for spec, runner, is_mock, fb in resolved
    ]
    # Include skipped models so meta reflects all requested slots.
    for name in skipped:
        model_states.append({"name": name, "runner": "skipped", "is_mock": False})
    meta = _make_meta(cfg, model_states)

    per_model: dict[str, ModelSummary] = {
        spec.name: ModelSummary(name=spec.name, is_mock=ismock, fallback=fb,
                                n_ok=0, n_error=0)
        for spec, _, ismock, fb in resolved
    }
    for name in skipped:
        per_model[name] = ModelSummary(name=name, is_mock=False, fallback=False,
                                       n_ok=0, n_error=0)
    n_completions = n_ok = n_err = 0

    for spec, runner, is_mock, fb in resolved:
        for item in cfg.items:
            item_id = item.get("id", "?")
            content_hash = hash_item(item)
            msgs = P.messages(item)
            p_hash = P.prompt_hash(item)
            system, user = P.build_prompt(item)
            for rep in range(cfg.n_reps):
                seed = cfg.base_seed + rep
                resp = runner.complete(msgs, seed=seed, item=item)
                ok = resp.ok and bool(resp.text)
                record = {
                    "run_id": cfg.run_id,
                    "model": spec.name,
                    "model_id": spec.model,
                    "vendor": spec.vendor,
                    "is_mock": is_mock,
                    "fallback": fb,
                    "item_id": item_id,
                    "content_hash": content_hash,
                    "rep": rep,
                    "seed": seed,
                    "prompt_hash": p_hash,
                    "prompt_template_version": P.TEMPLATE_VERSION,
                    "temperature": spec.temperature,
                    "system": system,
                    "text": resp.text,
                    "reasoning": resp.reasoning,
                    "finish_reason": resp.finish_reason,
                    "prompt_tokens": resp.prompt_tokens,
                    "completion_tokens": resp.completion_tokens,
                    "total_tokens": resp.prompt_tokens + resp.completion_tokens,
                    "latency_ms": resp.latency_ms,
                    "cost_usd": resp.cost_usd,
                    "system_fingerprint": resp.system_fingerprint,
                    "error": resp.error,
                    "ok": ok,
                    "timestamp": dt.datetime.now(dt.timezone.utc).isoformat(),
                }
                store.log(record)
                # Full raw payload (incl. exact provider body) for audit.
                store.write_raw(
                    spec.name, item_id, rep,
                    {"record": {k: v for k, v in record.items()},
                     "raw": resp.raw},
                )
                n_completions += 1
                if ok:
                    n_ok += 1
                    per_model[spec.name].n_ok += 1
                else:
                    n_err += 1
                    per_model[spec.name].n_error += 1

    finished = dt.datetime.now(dt.timezone.utc).isoformat()
    meta["finished_at"] = finished
    meta["n_completions"] = n_completions
    meta["n_ok"] = n_ok
    meta["n_error"] = n_err
    store.write_meta(meta)  # single finalise write

    return RunReport(
        run_id=cfg.run_id,
        run_dir=str(store.run_dir),
        n_models=len(cfg.models),
        n_items=len(cfg.items),
        n_reps=cfg.n_reps,
        n_completions=n_completions,
        n_ok=n_ok,
        n_error=n_err,
        models=[per_model.get(s.name, ModelSummary(name=s.name, is_mock=False,
                                                   fallback=False, n_ok=0, n_error=0))
                for s in cfg.models],
        started_at=started,
        finished_at=finished,
    )
