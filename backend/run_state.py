"""Background run orchestration + SSE streaming.

Manages in-flight runs and provides an SSE endpoint that streams progress as
records are written to the append-only log.
"""

from __future__ import annotations

import asyncio
import json
import os
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, AsyncIterator

from auslex.canary import GLOBAL_CANARY
from auslex.config import ModelSpec, default_models, load_models, resolve_api_key, is_real
from auslex.io import read_jsonl
from auslex.run.orchestrator import RunConfig, RunReport, probe_local
from auslex.run.storage import RunStore
from auslex.score.score import score_run
from auslex.stats.report import build_report, write_report


@dataclass
class InFlightRun:
    run_id: str
    report: RunReport
    stop_event: threading.Event = field(default_factory=threading.Event)


class RunManager:
    """Singleton managing in-flight and completed runs."""

    def __init__(self, out_root: Path = Path("runs")):
        self.out_root = out_root
        self._runs: dict[str, InFlightRun] = {}
        self._lock = threading.Lock()
        self._record_waiters: dict[str, list[asyncio.Future]] = {}
        self._record_count: dict[str, int] = {}

    def start_run(self, cfg: RunConfig) -> str:
        """Launch a run in the background and return its run_id."""
        run_id = cfg.run_id or f"auslex-{int(time.time())}"
        with self._lock:
            self._runs[run_id] = InFlightRun(run_id=run_id, report=RunReport(
                run_id=run_id, run_dir="", n_models=0, n_items=len(cfg.items),
                n_reps=cfg.n_reps, n_completions=0, n_ok=0, n_error=0,
                models=[], started_at="", finished_at="",
            ))
            self._record_count[run_id] = 0
        t = threading.Thread(target=self._run_worker, args=(cfg,), daemon=True)
        t.start()
        return run_id

    def _run_worker(self, cfg: RunConfig) -> None:
        """Execute the run, then score and stats."""
        from auslex.run.orchestrator import run
        from auslex.io import read_jsonl
        from auslex.score.score import score_run
        from auslex.stats.report import build_report, write_report

        try:
            # Load items (filter if requested).
            items = list(cfg.items)
            if cfg.question_filter:
                ids = {s.strip() for s in cfg.question_filter.split(",") if s.strip()}
                items = [it for it in items if it.get("id") in ids]
            if cfg.priestley_filter:
                areas = {s.strip() for s in cfg.priestley_filter.split(",") if s.strip()}
                items = [it for it in items if it.get("priestley_area") in areas]
            if cfg.jurisdiction_filter:
                jurs = {s.strip() for s in cfg.jurisdiction_filter.split(",") if s.strip()}
                items = [it for it in items if any(j in jurs for j in it.get("jurisdiction", []))]
            if cfg.difficulty_filter:
                diffs = {s.strip() for s in cfg.difficulty_filter.split(",") if s.strip()}
                items = [it for it in items if it.get("difficulty") in diffs]

            cfg = RunConfig(
                models=cfg.models,
                items=items,
                n_reps=cfg.n_reps,
                run_id=cfg.run_id,
                out_root=cfg.out_root,
                base_seed=cfg.base_seed,
            )

            # Override env vars for keys during the run.
            saved_env: dict[str, str] = {}
            key_map = {
                "openai": "OPENAI_API_KEY",
                "anthropic": "ANTHROPIC_API_KEY",
                "google": "GOOGLE_API_KEY",
            }
            for provider, env_var in key_map.items():
                val = _get_stored_key(provider)
                if val and val != os.environ.get(env_var):
                    saved_env[env_var] = os.environ.get(env_var, "")
                    os.environ[env_var] = val

            try:
                report = run(cfg)
            finally:
                for env_var, old in saved_env.items():
                    if old:
                        os.environ[env_var] = old
                    else:
                        os.environ.pop(env_var, None)

            with self._lock:
                if run_id in self._runs:
                    self._runs[run_id].report = report

            # Notify waiters.
            self._notify_waiters(run_id)

            # Score.
            scored_path = Path(report.run_dir) / "records.jsonl"
            srep = score_run(report.run_dir, items)

            # Stats.
            stats_dir = Path(self.out_root) / "scores" / report.run_id
            stats_scored = stats_dir / "scored.jsonl"
            report_stats = build_report(
                stats_scored, run_id=report.run_id,
                n_boot=cfg.n_reps * 1000, n_perm=cfg.n_reps * 1000, seed=cfg.base_seed,
            )
            write_report(report_stats, self.out_root)

            # Write contamination note to meta.
            store = RunStore(cfg.out_root, report.run_id)
            meta = store.read_meta()
            meta["contamination_note"] = (
                f"Every item embeds the global canary {GLOBAL_CANARY} plus a per-item "
                "canary derived from its id; reproducing either verbatim flags "
                "training-data contamination."
            )
            store.write_meta(meta)

            with self._lock:
                r = self._runs.get(run_id)
                if r:
                    r.report = report

        except Exception as e:
            with self._lock:
                if run_id in self._runs:
                    r = self._runs[run_id]
                    r.report = RunReport(
                        run_id=run_id, run_dir="", n_models=len(cfg.models),
                        n_items=len(cfg.items), n_reps=cfg.n_reps,
                        n_completions=0, n_ok=0, n_error=0,
                        models=[], started_at="", finished_at="",
                    )

        self._notify_waiters(run_id)

    def _notify_waiters(self, run_id: str) -> None:
        """Wake all waiters for a run."""
        with self._lock:
            waiters = self._record_waiters.pop(run_id, [])
            count = self._record_count.get(run_id, 0)
        for f in waiters:
            f.set_result(count)

    async def stream_records(self, run_id: str) -> AsyncIterator[str]:
        """Yield SSE events for run progress.

        Each event is a JSON line with the current record count.
        """
        store = RunStore(self.out_root, run_id)
        last_count = 0
        while True:
            if self.stop_event_is_set(run_id):
                yield f"data: {{\"type\": \"done\"}}\n\n"
                return
            records = store.records()
            count = len(records)
            if count != last_count:
                yield f"data: {{\"type\": \"progress\", \"count\": {count}, \"total\": {self._total_completions(run_id)}}}\n\n"
                last_count = count
                self._record_count[run_id] = count
            if self.is_done(run_id):
                yield f"data: {{\"type\": \"done\"}}\n\n"
                return
            await asyncio.sleep(0.5)

    def stop_event_is_set(self, run_id: str) -> bool:
        with self._lock:
            r = self._runs.get(run_id)
            return r.stop_event.is_set() if r else True

    def is_done(self, run_id: str) -> bool:
        with self._lock:
            r = self._runs.get(run_id)
            if not r:
                return True
            return r.report.finished_at != ""

    def _total_completions(self, run_id: str) -> int:
        with self._lock:
            r = self._runs.get(run_id)
            if not r:
                return 0
            return r.report.n_completions

    def get_run_status(self, run_id: str) -> dict[str, Any]:
        with self._lock:
            r = self._runs.get(run_id)
        if not r:
            # Check disk.
            store = RunStore(self.out_root, run_id)
            if store.meta_path.exists():
                meta = store.read_meta()
                return {
                    "run_id": run_id,
                    "status": "done" if meta.get("finished_at") else "running",
                    "n_completions": meta.get("n_completions", 0),
                    "n_total": meta.get("n_reps", 3) * len(meta.get("items", [])) * len(meta.get("models", [])),
                    "n_ok": meta.get("n_ok", 0),
                    "n_error": meta.get("n_error", 0),
                    "models": meta.get("models", []),
                    "started_at": meta.get("started_at"),
                    "finished_at": meta.get("finished_at"),
                }
            return {"run_id": run_id, "status": "error", "error_msg": "run not found"}
        rp = r.report
        return {
            "run_id": run_id,
            "status": "done" if rp.finished_at else "running",
            "n_completions": rp.n_completions,
            "n_total": rp.n_models * rp.n_items * rp.n_reps,
            "n_ok": rp.n_ok,
            "n_error": rp.n_error,
            "models": [
                {
                    "name": m.name,
                    "is_mock": m.is_mock,
                    "n_done": m.n_ok + m.n_error,
                    "n_total": rp.n_items * rp.n_reps,
                    "n_ok": m.n_ok,
                    "n_error": m.n_error,
                    "status": "done" if (m.n_ok + m.n_error) >= rp.n_items * rp.n_reps else "running",
                }
                for m in rp.models
            ],
            "started_at": rp.started_at,
            "finished_at": rp.finished_at,
        }


# --------------------------------------------------------------------------- #
# Key helpers
# --------------------------------------------------------------------------- #


def _get_stored_key(provider: str) -> Optional[str]:
    """Get a key from env or the secrets store."""
    env_var = {
        "openai": "OPENAI_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
        "google": "GOOGLE_API_KEY",
    }.get(provider)
    if env_var:
        val = os.environ.get(env_var)
        if val:
            return val
    return load_secrets().get(provider)


def _apply_keys_to_env(cfg: RunConfig) -> dict[str, str]:
    """Temporarily set API keys from the secrets store into env."""
    saved: dict[str, str] = {}
    key_map = {
        "openai": "OPENAI_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
        "google": "GOOGLE_API_KEY",
    }
    for provider, env_var in key_map.items():
        val = _get_stored_key(provider)
        if val:
            saved[env_var] = os.environ.get(env_var, "")
            os.environ[env_var] = val
    return saved


def _restore_env(saved: dict[str, str]) -> None:
    for env_var, old in saved.items():
        if old:
            os.environ[env_var] = old
        else:
            os.environ.pop(env_var, None)
