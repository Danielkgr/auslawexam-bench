"""Build the public GitHub Pages site from committed real runs only.

A run is published only when every model in it ran for real.  A run with any
mock slot is left out, so the public site never shows synthetic numbers.
"""

from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any

from ..canary import GLOBAL_CANARY
from ..run.storage import RunStore
from ..stats.report import build_report, load_scored
from .site import publish_site

_INDEX = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>AusLawExam-Bench</title>
<style>
  :root {{ color-scheme: light dark; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial,
         sans-serif; margin: 0; padding: 2rem; max-width: 960px; line-height: 1.5; }}
  table {{ border-collapse: collapse; width: 100%; margin: 1rem 0; font-size: .92rem; }}
  th, td {{ border: 1px solid #8885; padding: .45rem .6rem; text-align: left; }}
  th {{ background: #8881; }}
  .num {{ text-align: right; font-variant-numeric: tabular-nums; }}
  .muted {{ color: #888; font-size: .85rem; }}
</style>
</head>
<body>
<h1>AusLawExam-Bench</h1>
<p>A reproducible benchmark of Australian legal reasoning for LLMs, scored on how often a
model invents a citation.  This site shows committed runs of real models only; mock runs are
never published here.  The 16 questions are provisional and not yet reviewed by a lawyer, and
the fabricated rate is an upper bound, because a real citation missing from the small known
corpus is counted as unconfirmed.</p>
<table>
<thead><tr><th>Run</th><th>Models</th><th class="num">Questions</th>
<th class="num">Mean score</th><th class="num">Fabricated rate (upper bound)</th></tr></thead>
<tbody>
{rows}
</tbody>
</table>
<p class="muted">Source, raw outputs, and method:
<a href="https://github.com/Danielkgr/auslawexam-bench">github.com/Danielkgr/auslawexam-bench</a>.</p>
</body>
</html>
"""


def _is_real_run(meta: dict[str, Any], rows: list[dict[str, Any]]) -> bool:
    models = [m for m in meta.get("models", []) if m.get("runner") != "skipped"]
    if not models or any(m.get("is_mock") for m in models):
        return False
    return bool(rows) and not any(r.get("is_mock") for r in rows)


def build_pages(output_root: str | Path, out_dir: str | Path) -> list[str]:
    """Publish every real run under ``output_root`` into ``out_dir``.

    Returns the ids of the runs published.
    """
    root, out = Path(output_root), Path(out_dir)
    published: list[tuple[str, dict[str, Any]]] = []
    runs_root = root / "runs"
    run_dirs = sorted(p for p in runs_root.iterdir() if p.is_dir()) if runs_root.exists() else []
    for run_dir in run_dirs:
        run_id = run_dir.name
        store = RunStore(runs_root, run_id, create_dirs=False)
        scored = root / "scores" / run_id / "scored.jsonl"
        if not store.meta_path.exists() or not scored.exists():
            continue
        meta = store.read_meta()
        if not _is_real_run(meta, load_scored(scored)):
            continue
        stats_json = root / "stats" / run_id / "stats.json"
        report = (
            json.loads(stats_json.read_text(encoding="utf-8"))
            if stats_json.exists()
            else build_report(scored, run_id=run_id)
        )
        meta["contamination_note"] = (
            f"Every item embeds the global canary {GLOBAL_CANARY} plus a per-item canary "
            "derived from its id; reproducing either verbatim flags training-data contamination."
        )
        publish_site(out / run_id, report=report, meta=meta)
        published.append((run_id, report))

    rows = []
    for run_id, report in published:
        models = report.get("models", [])
        names = ", ".join(html.escape(m["model"]) for m in models)
        score = "; ".join(f"{m['mean_item_score_100']['point']:.1f}" for m in models)
        fab = "; ".join(f"{m['fabricated_rate']['point']:.3f}" for m in models)
        rows.append(
            f"<tr><td><a href='./{html.escape(run_id)}/'>{html.escape(run_id)}</a></td>"
            f"<td>{names}</td><td class='num'>{report.get('n_questions_total', '')}</td>"
            f"<td class='num'>{score}</td><td class='num'>{fab}</td></tr>"
        )
    out.mkdir(parents=True, exist_ok=True)
    body = "\n".join(rows) or "<tr><td colspan='5'>No real runs yet.</td></tr>"
    (out / "index.html").write_text(_INDEX.format(rows=body), encoding="utf-8")
    return [run_id for run_id, _ in published]
