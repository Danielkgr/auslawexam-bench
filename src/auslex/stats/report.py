"""Build the per-run statistics report.

Reads the score layer's ``scored.jsonl`` (one line per model/item/rep) and
produces:

- ``stats/<run-id>/stats.json`` — machine-readable: per-model means with
  bootstrap CIs (question-level), pairwise permutation p-values, and
  per-difficulty / per-Priestley-area breakdowns.
- ``stats/<run-id>/report.md``  — a human-readable summary table.

Everything is seeded and reproducible.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .bootstrap import bootstrap_ci
from .permutation import paired_permutation


def load_scored(path: str | Path) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    p = Path(path)
    if not p.exists():
        return out
    with open(p, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def _mean(xs: list[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def _question_level(
    rows: list[dict[str, Any]], model: str, key: str
) -> dict[str, float]:
    """Mean of ``key`` across reps, per (model, question)."""
    acc: dict[str, list[float]] = {}
    for r in rows:
        if r.get("model") != model:
            continue
        acc.setdefault(r["item_id"], []).append(float(r.get(key, 0.0)))
    return {q: _mean(v) for q, v in acc.items()}


def _group_means(rows, model, group_field):
    acc: dict[str, list[float]] = {}
    for r in rows:
        if r.get("model") != model:
            continue
        g = r.get(group_field)
        acc.setdefault(g, []).append(float(r.get("item_score_100", 0.0)))
    return {g: round(_mean(v), 2) for g, v in sorted(acc.items(), key=lambda kv: str(kv[0]))}


def build_report(
    scored_path: str | Path,
    *,
    run_id: str,
    n_boot: int = 10_000,
    n_perm: int = 10_000,
    seed: int = 0,
) -> dict[str, Any]:
    rows = load_scored(scored_path)
    models = sorted({r["model"] for r in rows})

    # Question-level aggregates per model (mean across reps).
    q_scores: dict[str, dict[str, float]] = {}
    q_fab: dict[str, dict[str, float]] = {}
    for m in models:
        q_scores[m] = _question_level(rows, m, "item_score_100")
        acc: dict[str, list[float]] = {}
        for r in rows:
            if r.get("model") != m:
                continue
            fr = (r.get("citations") or {}).get("fabricated_rate", 0.0)
            acc.setdefault(r["item_id"], []).append(float(fr))
        q_fab[m] = {q: _mean(v) for q, v in acc.items()}

    model_stats: list[dict[str, Any]] = []
    mock_models = {r["model"] for r in rows if r.get("is_mock")}
    for m in models:
        scores = list(q_scores[m].values())
        fabs = list(q_fab[m].values())
        score_ci = bootstrap_ci(scores, n_boot=n_boot, ci=0.95, seed=seed)
        fab_ci = bootstrap_ci(fabs, n_boot=n_boot, ci=0.95, seed=seed + 1)
        model_stats.append({
            "model": m,
            "is_mock": m in mock_models,
            "n_questions": len(scores),
            "mean_item_score_100": {
                "point": round(_mean(scores), 2),
                "ci95": [round(score_ci.low, 2), round(score_ci.high, 2)],
            },
            "fabricated_rate": {
                "point": round(_mean(fabs), 4),
                "ci95": [round(fab_ci.low, 4), round(fab_ci.high, 4)],
            },
            "per_difficulty": _group_means(rows, m, "difficulty"),
            "per_priestley": _group_means(rows, m, "priestley_area"),
            "ci_seed": score_ci.to_dict(),
        })

    # Pairwise permutation tests (leaderboard order: higher score first).
    order = sorted(model_stats, key=lambda x: -x["mean_item_score_100"]["point"])
    pairs: list[dict[str, Any]] = []
    for i in range(len(order)):
        for j in range(i + 1, len(order)):
            ma, mb = order[i]["model"], order[j]["model"]
            res = paired_permutation(
                q_scores[ma], q_scores[mb],
                a_name=ma, b_name=mb, n_perm=n_perm, seed=seed,
            )
            pairs.append(res.to_dict())

    report = {
        "run_id": run_id,
        "n_questions_total": len({r["item_id"] for r in rows}),
        "n_models": len(models),
        "models": order,
        "pairwise_permutation": pairs,
        "method": {
            "ci": f"percentile bootstrap, n_boot={n_boot}, question-level, seeded",
            "comparison": f"paired permutation (sign-flip), n_perm={n_perm}, two-sided, seeded",
            "seed": seed,
        },
    }
    return report


def _fmt_ci(x: dict) -> str:
    lo, hi = x["ci95"]
    return f"{x['point']:.1f} [{lo:.1f}, {hi:.1f}]"


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        f"# AusLawExam-Bench — Run Report",
        "",
        f"Run `{report['run_id']}` · {report['n_models']} models · "
        f"{report['n_questions_total']} questions.",
        "",
        "## Leaderboard (item score, 0–100, 95% CI)",
        "",
        "| Model | Mean score (95% CI) | Fabricated-citation rate (95% CI) | Questions |",
        "|---|---|---|---|",
    ]
    for m in report["models"]:
        fr = m["fabricated_rate"]
        lines.append(
            f"| {m['model']} | {_fmt_ci(m['mean_item_score_100'])} | "
            f"{fr['point']:.3f} [{fr['ci95'][0]:.3f}, {fr['ci95'][1]:.3f}] | "
            f"{m['n_questions']} |"
        )
    lines += [
        "",
        "## Pairwise significance (paired permutation, two-sided)",
        "",
        "| Model A | Model B | Mean diff (A−B) | p-value | Significant (α=.05) |",
        "|---|---|---|---|---|",
    ]
    for p in report["pairwise_permutation"]:
        sig = "**yes**" if p["significant_05"] else "no"
        lines.append(
            f"| {p['a']} | {p['b']} | {p['mean_diff']:+.2f} | {p['p_value']:.4f} | {sig} |"
        )
    lines += [
        "",
        f"*Method: {report['method']['ci']}; {report['method']['comparison']}.*",
        "",
    ]
    return "\n".join(lines)


def write_report(
    report: dict[str, Any], out_root: str | Path
) -> dict[str, str]:
    stats_dir = Path(out_root) / "stats" / report["run_id"]
    stats_dir.mkdir(parents=True, exist_ok=True)
    stats_json = stats_dir / "stats.json"
    report_md = stats_dir / "report.md"
    with open(stats_json, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2, sort_keys=True, default=str)
        fh.write("\n")
    report_md.write_text(render_markdown(report), encoding="utf-8")
    return {"stats_json": str(stats_json), "report_md": str(report_md)}
