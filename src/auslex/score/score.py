"""Score a completed run: citation validation + rubric judge per completion,
then per-model aggregates written to ``scores/<run-id>/``.

Outputs:
- ``scored.jsonl``    — one line per (model, item, rep): item score (0-100),
  citation report, rubric breakdown, judge details, and the item's metadata
  (Priestley area, difficulty, topics) so the stats layer can slice it.
- ``score_summary.json`` — per-model aggregates (mean score, fabricated-citation
  rate, per-difficulty / per-Priestley breakdowns).
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Optional

from ..run.storage import RunStore
from .citations import assess_answer, build_known_corpus, CitationReport
from .judge import JudgeConfig, judge_answer


@dataclass
class ModelScore:
    model: str
    model_id: str
    is_mock: bool
    n_items: int
    n_completed: int
    n_error: int
    mean_item_score_100: float
    fabricated_rate: float
    on_point_rate: float
    avg_citations: float
    per_difficulty: dict[str, dict] = field(default_factory=dict)
    per_priestley: dict[str, dict] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ScoreReport:
    run_id: str
    scores_dir: str
    n_scored: int
    models: list[ModelScore]

    def to_dict(self) -> dict[str, Any]:
        return {"run_id": self.run_id, "scores_dir": self.scores_dir,
                "n_scored": self.n_scored,
                "models": [m.to_dict() for m in self.models]}


def _mean(xs: list[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def score_run(
    run_dir: str | Path,
    items: list[dict[str, Any]],
    *,
    corpus: Optional[set[str]] = None,
    judge_cfg: Optional[JudgeConfig] = None,
    out_root: str | Path | None = None,
) -> ScoreReport:
    run_dir = Path(run_dir)
    run_id = run_dir.name
    store = RunStore(run_dir.parent, run_id)
    records = store.records()

    item_by_id = {it["id"]: it for it in items}
    if corpus is None:
        corpus = build_known_corpus(items)
    judge_cfg = judge_cfg or JudgeConfig()

    scores_dir = (Path(out_root) if out_root else run_dir.parent.parent / "scores") / run_id
    scores_dir.mkdir(parents=True, exist_ok=True)
    scored_path = scores_dir / "scored.jsonl"
    if scored_path.exists():
        scored_path.unlink()  # scoring is idempotent / re-runnable

    by_model: dict[str, dict[str, list[float]]] = {}
    n_scored = 0

    with open(scored_path, "w", encoding="utf-8") as fh:
        for rec in records:
            if not rec.get("ok") or not rec.get("text"):
                continue
            item = item_by_id.get(rec["item_id"])
            if item is None:
                continue
            cite: CitationReport = assess_answer(item, rec["text"], corpus)
            judged = judge_answer(item, rec["text"], judge_cfg, seed=rec.get("seed"))
            row = {
                "run_id": run_id,
                "model": rec["model"],
                "model_id": rec.get("model_id"),
                "item_id": rec["item_id"],
                "rep": rec.get("rep"),
                "is_mock": rec.get("is_mock", False),
                "priestley_area": item.get("priestley_area"),
                "difficulty": item.get("difficulty"),
                "topics": item.get("topics", []),
                "item_score_100": round(judged.item_score * 100.0, 3),
                "citations": cite.to_dict(),
                "rubric": judged.per_criterion,
                "judge": judged.to_dict(),
            }
            fh.write(json.dumps(row, sort_keys=True, default=str) + "\n")
            n_scored += 1

            m = by_model.setdefault(
                rec["model"],
                {
                    "model_id": rec.get("model_id"),
                    "is_mock": rec.get("is_mock", False),
                    "scores": [], "fab": [], "op": [], "ncite": [],
                    "items": set(), "n_err": 0,
                    "per_diff": {}, "per_pri": {},
                },
            )
            m["scores"].append(row["item_score_100"])
            m["fab"].append(cite.fabricated_rate)
            m["op"].append(cite.on_point_rate)
            m["ncite"].append(cite.total)
            m["items"].add(rec["item_id"])
            d = item.get("difficulty")
            m["per_diff"].setdefault(d, []).append(row["item_score_100"])
            p = item.get("priestley_area")
            m["per_pri"].setdefault(p, []).append(row["item_score_100"])

    # Fold in error counts from records that didn't score.
    err_counts: dict[str, int] = {}
    for rec in records:
        if not rec.get("ok"):
            err_counts[rec["model"]] = err_counts.get(rec["model"], 0) + 1

    models: list[ModelScore] = []
    for name, m in by_model.items():
        models.append(ModelScore(
            model=name,
            model_id=m["model_id"] or name,
            is_mock=m["is_mock"],
            n_items=len(m["items"]),
            n_completed=len(m["scores"]),
            n_error=err_counts.get(name, 0),
            mean_item_score_100=round(_mean(m["scores"]), 2),
            fabricated_rate=round(_mean(m["fab"]), 4),
            on_point_rate=round(_mean(m["op"]), 4),
            avg_citations=round(_mean(m["ncite"]), 2),
            per_difficulty={
                k: {"n": len(v), "mean_item_score_100": round(_mean(v), 2)}
                for k, v in sorted(m["per_diff"].items())
            },
            per_priestley={
                k: {"n": len(v), "mean_item_score_100": round(_mean(v), 2)}
                for k, v in sorted(m["per_pri"].items())
            },
        ))
    models.sort(key=lambda x: (-x.mean_item_score_100, x.fabricated_rate))

    summary = {
        "run_id": run_id,
        "n_scored": n_scored,
        "judge": judge_cfg.name,
        "models": [m.to_dict() for m in models],
    }
    with open(scores_dir / "score_summary.json", "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2, sort_keys=True, default=str)
        fh.write("\n")

    return ScoreReport(run_id=run_id, scores_dir=str(scores_dir),
                       n_scored=n_scored, models=models)
