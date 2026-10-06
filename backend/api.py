"""FastAPI routes for the AusLawExam-Bench Evaluator."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Any, AsyncIterator

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from auslex.io import read_jsonl

from .models import (
    ApiKeyConfig,
    CitationAudit,
    ItemResult,
    LeaderboardModel,
    LocalProbeResult,
    PairwiseResult,
    QuestionDetail,
    QuestionListItem,
    RunConfig,
    RunStatus,
    SlotStatus,
    StatsReport,
    TestConnectionResult,
)
from .run_state import RunManager, _apply_keys_to_env, _get_stored_key, _restore_env
from auslex.run.orchestrator import probe_local, RunConfig as OrchestrationRunConfig
from auslex.run.storage import RunStore
from auslex.runners import get_runner
from auslex.score.citations import _matches, _norm
import dataclasses
import re

router = APIRouter(prefix="/api")

# --------------------------------------------------------------------------- #
# State
# --------------------------------------------------------------------------- #

# Project root is the parent of backend/.
ROOT = Path(__file__).resolve().parents[1]
DEFAULT_QUESTIONS = ROOT / "data" / "questions" / "auslex.jsonl"
# The output root holds runs/, scores/, stats/, and site/, as for the CLI's
# --out-root.  AUSLEX_OUT_ROOT moves all of them together.
OUTPUT_ROOT = Path(os.environ.get("AUSLEX_OUT_ROOT") or ROOT)

run_manager = RunManager(output_root=OUTPUT_ROOT)

# The key store is per provider; the slots that provider's key unlocks.
PROVIDER_SLOT = {"openai": "gpt", "anthropic": "claude", "google": "gemini"}


def _runs_root() -> Path:
    return OUTPUT_ROOT / "runs"


def _scored_path(run_id: str) -> Path:
    return OUTPUT_ROOT / "scores" / run_id / "scored.jsonl"


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

# Strict run_id pattern: alphanum + underscore, dot, hyphen (no ../ or /).
_RUN_ID_RE = re.compile(r"^[A-Za-z0-9._-]+$")


def _validate_run_id(run_id: str) -> None:
    """Raise HTTPException(400) if run_id contains path traversal chars."""
    if not run_id or not _RUN_ID_RE.match(run_id):
        raise HTTPException(status_code=400, detail=f"invalid run_id {run_id!r}")


def _safe_path(base: Path, run_id: str) -> Path:
    """Resolve base/run_id and verify it stays under base."""
    p = (base / run_id).resolve()
    root = base.resolve()
    if not str(p).startswith(str(root)):
        raise HTTPException(status_code=400, detail=f"path traversal in run_id {run_id!r}")
    return p


def _load_questions() -> list[dict[str, Any]]:
    from auslex.io import read_jsonl
    return read_jsonl(DEFAULT_QUESTIONS)


def _spec_to_status(spec: Any) -> SlotStatus:
    from auslex.config import is_real
    key = _get_stored_key(spec.vendor) or (
        os.environ.get(spec.api_key_env) if spec.api_key_env else None
    )
    reachable: bool | None = None
    if spec.vendor == "local":
        reachable = probe_local(spec.base_url or "")
    return SlotStatus(
        name=spec.name,
        vendor=spec.vendor,
        model=spec.model,
        is_real=is_real(spec) and (spec.vendor != "local" or reachable),
        is_mock=not (is_real(spec) and (spec.vendor != "local" or reachable)),
        is_reachable=reachable,
        key_present=bool(key),
        base_url=spec.base_url,
    )


# --------------------------------------------------------------------------- #
# Endpoints
# --------------------------------------------------------------------------- #


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/slots")
async def get_slots() -> list[dict[str, Any]]:
    """Return the eight model slots with their real or mock status."""
    from auslex.config import default_models
    specs = default_models()
    return [_spec_to_status(s).model_dump() for s in specs]


@router.get("/questions")
async def list_questions() -> list[dict[str, Any]]:
    """Return the question set as a list of lightweight items."""
    items = _load_questions()
    return [
        {
            "id": it["id"],
            "type": it["type"],
            "priestley_area": it["priestley_area"],
            "jurisdiction": it["jurisdiction"],
            "difficulty": it["difficulty"],
            "marks": it["marks"],
        }
        for it in items
    ]


@router.get("/questions/{question_id}")
async def get_question(question_id: str) -> dict[str, Any]:
    """Return full detail for one question."""
    items = _load_questions()
    for it in items:
        if it["id"] == question_id:
            return {
                "id": it["id"],
                "type": it["type"],
                "priestley_area": it["priestley_area"],
                "jurisdiction": it["jurisdiction"],
                "difficulty": it["difficulty"],
                "marks": it["marks"],
                "question_text": it["question_text"],
                "facts": it.get("facts"),
                "instructions": it.get("instructions"),
                "gold_answer": it["gold_answer"],
                "required_authorities": it.get("required_authorities", []),
                "rubric": it.get("rubric", []),
                "topics": it.get("topics", []),
                "canary": it.get("canary", ""),
            }
    raise HTTPException(status_code=404, detail=f"question {question_id} not found")


@router.get("/keys")
async def get_keys() -> ApiKeyConfig:
    """Return key presence indicators (never the keys themselves)."""
    return ApiKeyConfig(
        openai_key=_get_stored_key("openai"),
        anthropic_key=_get_stored_key("anthropic"),
        google_key=_get_stored_key("google"),
        local_base_url=os.environ.get("AUSLEX_LOCAL_BASE_URL", "http://localhost:10000/v1"),
        local_model=os.environ.get("AUSLEX_LOCAL_MODEL", ""),
        local_enable_thinking=bool(int(os.environ.get("AUSLEX_LOCAL_ENABLE_THINKING", "0"))),
    )


@router.put("/keys")
async def set_keys(cfg: ApiKeyConfig) -> dict[str, str]:
    """Store API keys (local-only, never logged)."""
    from .secrets import set_key, delete_key
    if cfg.openai_key:
        set_key("openai", cfg.openai_key)
    else:
        delete_key("openai")
    if cfg.anthropic_key:
        set_key("anthropic", cfg.anthropic_key)
    else:
        delete_key("anthropic")
    if cfg.google_key:
        set_key("google", cfg.google_key)
    else:
        delete_key("google")
    # Env overrides for local slot.
    if cfg.local_base_url:
        os.environ["AUSLEX_LOCAL_BASE_URL"] = cfg.local_base_url
    else:
        os.environ.pop("AUSLEX_LOCAL_BASE_URL", None)
    if cfg.local_model:
        os.environ["AUSLEX_LOCAL_MODEL"] = cfg.local_model
    else:
        os.environ.pop("AUSLEX_LOCAL_MODEL", None)
    os.environ["AUSLEX_LOCAL_ENABLE_THINKING"] = "1" if cfg.local_enable_thinking else "0"
    return {"status": "ok"}


@router.post("/keys/test/{provider}")
async def test_connection(provider: str) -> TestConnectionResult:
    """Test a provider connection with a minimal completion."""
    from auslex.config import default_models

    if provider not in PROVIDER_SLOT:
        return TestConnectionResult(ok=False, detail=f"Unknown provider {provider!r}")

    key = _get_stored_key(provider)
    if not key:
        return TestConnectionResult(ok=False, detail=f"No key configured for {provider}")

    # Set env var so the runner picks it up.
    env_map = {"openai": "OPENAI_API_KEY", "anthropic": "ANTHROPIC_API_KEY", "google": "GOOGLE_API_KEY"}
    env_var = env_map.get(provider)
    old = os.environ.get(env_var)
    if env_var:
        os.environ[env_var] = key

    try:
        # The provider is "openai", "anthropic" or "google"; the slot that
        # uses its key is named "gpt", "claude" or "gemini".
        slot = PROVIDER_SLOT[provider]
        spec = next(s for s in default_models() if s.name == slot)
        # A short answer is enough to prove the key and the request work.
        spec = dataclasses.replace(spec, max_tokens=1024, extra={**spec.extra, "effort": "low"})
        runner = get_runner(spec, allow_mock_fallback=False)
        msgs = [{"role": "user", "content": "Say: hello"}]
        resp = runner.complete(msgs, seed=0)
        # A truncated reply still proves the connection works.
        connected = resp.error is None or resp.error.startswith("truncated")
        return TestConnectionResult(
            ok=connected,
            detail=resp.error or "ok",
            model_id=resp.model,
        )
    except Exception as e:
        return TestConnectionResult(ok=False, detail=str(e))
    finally:
        if env_var:
            if old:
                os.environ[env_var] = old
            else:
                os.environ.pop(env_var, None)


@router.post("/runs", status_code=201)
async def create_run(cfg: RunConfig) -> dict[str, str]:
    """Start a new run and return its run_id."""
    from auslex.config import load_models
    from auslex.io import read_jsonl

    items = read_jsonl(DEFAULT_QUESTIONS)

    # Apply key env vars.
    saved = _apply_keys_to_env(cfg)
    try:
        specs = load_models()
        wanted = [s for s in specs if s.name in cfg.models]
        if not wanted:
            raise HTTPException(status_code=400, detail="no valid model slots selected")

        run_cfg = OrchestrationRunConfig(
            models=wanted,
            items=items,
            n_reps=cfg.n_reps,
            run_id=cfg.run_id,
            out_root=_runs_root(),
            base_seed=cfg.base_seed,
        )
        run_id = run_manager.start_run(run_cfg)
        return {"run_id": run_id}
    finally:
        _restore_env(saved)


@router.get("/runs/{run_id}/status")
async def get_run_status(run_id: str) -> dict[str, Any]:
    """Get the current status of a run."""
    _validate_run_id(run_id)
    return run_manager.get_run_status(run_id)


@router.get("/runs/{run_id}/stream")
async def stream_run(run_id: str) -> StreamingResponse:
    """SSE stream for run progress."""
    _validate_run_id(run_id)
    async def event_stream() -> AsyncIterator[str]:
        async for event in run_manager.stream_records(run_id):
            yield event

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.get("/runs")
async def list_runs() -> list[dict[str, Any]]:
    """List all past runs."""
    root = _runs_root()
    run_ids = sorted(p.name for p in root.iterdir() if p.is_dir()) if root.exists() else []
    result = []
    for rid in reversed(run_ids):
        s = RunStore(root, rid, create_dirs=False)
        if s.meta_path.exists():
            meta = s.read_meta()
            result.append({
                "run_id": rid,
                "started_at": meta.get("started_at", ""),
                "finished_at": meta.get("finished_at", ""),
                "n_models": len(meta.get("models", [])),
                "n_items": len(meta.get("items", [])),
                "n_reps": meta.get("n_reps", 0),
                "n_completions": meta.get("n_completions", 0),
                "n_ok": meta.get("n_ok", 0),
                "n_error": meta.get("n_error", 0),
                "models": [m.get("name") for m in meta.get("models", [])],
            })
    return result


@router.get("/runs/{run_id}/report")
async def get_report(run_id: str) -> dict[str, Any]:
    """Get the stats report for a run."""
    _validate_run_id(run_id)
    scored_path = _scored_path(run_id)
    if not scored_path.exists():
        raise HTTPException(status_code=404, detail=f"no scored data for run {run_id}")
    from auslex.stats.report import build_report
    report = build_report(scored_path, run_id=run_id)
    return report


@router.get("/runs/{run_id}/item-results")
async def get_item_results(
    run_id: str,
    model: str | None = None,
    question: str | None = None,
) -> list[dict[str, Any]]:
    """Get per-item results for a run, with optional filters."""
    _validate_run_id(run_id)
    from auslex.score.citations import build_known_corpus
    scored_path = _scored_path(run_id)
    if not scored_path.exists():
        raise HTTPException(status_code=404, detail=f"no scored data for run {run_id}")
    rows = read_jsonl(scored_path)
    if model:
        rows = [r for r in rows if r.get("model") == model]
    if question:
        rows = [r for r in rows if r.get("item_id") == question]

    items = _load_questions()
    item_by_id = {it["id"]: it for it in items}
    corpus = build_known_corpus(items)
    # The answer text lives in the run's own records, not in the scores.
    store = RunStore(_runs_root(), run_id, create_dirs=False)
    texts = {(r.get("model"), r.get("item_id"), r.get("rep")): r.get("text")
             for r in store.records()}

    results = []
    for row in rows:
        item = item_by_id.get(row.get("item_id"))
        cites = row.get("citations", {})
        # Use the scorer's own class for each citation when it was recorded.
        citation_audits = []
        if cites.get("citations") and all(c.get("class") for c in cites["citations"]):
            citation_audits = [
                CitationAudit(kind=c["kind"], raw=c["raw"], classification=c["class"])
                for c in cites["citations"]
            ]
        elif item and cites.get("citations"):
            req_cites = {
                _norm(a.get("cite", ""))
                for a in item.get("required_authorities", [])
            }
            for c in cites["citations"]:
                cn = _norm(c["raw"])
                if any(_matches(cn, r) for r in req_cites):
                    cls = "on_point"
                elif any(_matches(cn, ref) for ref in corpus):
                    cls = "known_other"
                else:
                    cls = "fabricated"
                citation_audits.append(CitationAudit(
                    kind=c["kind"], raw=c["raw"], classification=cls
                ))

        # Check contamination.
        contamination = False
        if item:
            from auslex.canary import find_canaries, make_canary
            item_canary = make_canary(item["id"])
            text = texts.get((row.get("model"), row.get("item_id"), row.get("rep"))) or ""
            found = find_canaries(text)
            contamination = item_canary in found or any(item_canary in c for c in found)

        results.append({
            "run_id": run_id,
            "model": row.get("model"),
            "item_id": row.get("item_id"),
            "rep": row.get("rep"),
            "is_mock": row.get("is_mock", False),
            "priestley_area": row.get("priestley_area"),
            "difficulty": row.get("difficulty"),
            "item_score_100": row.get("item_score_100", 0),
            "fabricated_rate": cites.get("fabricated_rate", 0),
            "on_point_rate": cites.get("on_point_rate", 0),
            "total_citations": cites.get("total", 0),
            "citations": [ca.model_dump() for ca in citation_audits],
            "rubric": row.get("rubric", {}),
            "answer_text": texts.get((row.get("model"), row.get("item_id"), row.get("rep"))),
            "contamination_flag": contamination,
        })
    return results


@router.get("/runs/{run_id}/records")
async def get_records(run_id: str) -> list[dict[str, Any]]:
    """Get raw records for a run."""
    _validate_run_id(run_id)
    return RunStore(_runs_root(), run_id, create_dirs=False).records()


@router.get("/local/probe")
async def probe_local_endpoint() -> dict[str, Any]:
    """Probe the local llama.cpp endpoint."""
    url = os.environ.get("AUSLEX_LOCAL_BASE_URL", "http://localhost:10000/v1")
    reachable = probe_local(url)
    models: list[dict[str, Any]] = []
    error: str | None = None
    if reachable:
        try:
            import urllib.request
            with urllib.request.urlopen(url.rstrip("/") + "/models", timeout=5) as r:
                data = __import__("json").loads(r.read().decode("utf-8"))
            models = data.get("data", data if isinstance(data, list) else [])
        except Exception as e:
            error = str(e)
    return LocalProbeResult(reachable=reachable, models=models, error=error).model_dump()


@router.post("/runs/{run_id}/export-site")
async def export_site(run_id: str) -> dict[str, str]:
    """Re-render the static leaderboard site for a run."""
    from auslex.publish import publish_site
    from auslex.stats.report import build_report

    _validate_run_id(run_id)
    scored_path = _scored_path(run_id)
    if not scored_path.exists():
        raise HTTPException(status_code=404, detail=f"no scored data for run {run_id}")
    report = build_report(scored_path, run_id=run_id)
    store = RunStore(_runs_root(), run_id, create_dirs=False)
    meta = store.read_meta()
    meta["contamination_note"] = (
        f"Every item embeds the global canary plus a per-item canary derived "
        "from its id; reproducing either verbatim flags training-data contamination."
    )
    site_dir = OUTPUT_ROOT / "site" / run_id
    index = publish_site(site_dir, report=report, meta=meta)
    return {"site_path": str(index)}


@router.post("/runs/{run_id}/export-hf")
async def export_hf(run_id: str) -> dict[str, str]:
    """Export run outputs for Hugging Face."""
    _validate_run_id(run_id)
    store = RunStore(_runs_root(), run_id, create_dirs=False)
    if not store.run_dir.exists():
        raise HTTPException(status_code=404, detail=f"run {run_id} not found")

    from auslex.publish.export_hf import build_hf_export

    items = _load_questions()
    out = OUTPUT_ROOT / "export" / "hf" / run_id
    exp = build_hf_export(out, items, name=f"auslex-{run_id}", version="0.1.0")
    return {"export_path": str(out), "n_items": str(exp.n_items), "files": ", ".join(exp.files)}


@router.get("/runs/{run_id}/download")
async def download_run(run_id: str) -> dict[str, str]:
    """Return paths for downloading raw run outputs."""
    _validate_run_id(run_id)
    store = RunStore(_runs_root(), run_id, create_dirs=False)
    if not store.run_dir.exists():
        raise HTTPException(status_code=404, detail=f"run {run_id} not found")
    return {
        "run_dir": str(store.run_dir),
        "meta": str(store.meta_path),
        "records": str(store.records_path),
        "raw_dir": str(store.raw_dir),
    }
