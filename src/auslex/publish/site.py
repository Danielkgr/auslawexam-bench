"""Render the public leaderboard as a self-contained static site.

The "site" is a single ``index.html`` (inline CSS, no external assets or JS
dependencies) suitable for dropping straight into GitHub Pages. It is built
from the stats report (leaderboard order, bootstrap CIs, pairwise p-values)
plus the run metadata, and is fully reproducible for a given run.
"""

from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any, Optional

_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>AusLawExam-Bench &middot; Leaderboard</title>
<style>
  :root {{ color-scheme: light dark; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
         margin: 0; padding: 2rem; max-width: 960px; line-height: 1.5; }}
  h1 {{ margin-top: 0; font-size: 1.6rem; }}
  h2 {{ font-size: 1.15rem; margin-top: 2rem; border-bottom: 1px solid #8884; padding-bottom: .3rem; }}
  table {{ border-collapse: collapse; width: 100%; margin: 1rem 0; font-size: .92rem; }}
  th, td {{ border: 1px solid #8885; padding: .45rem .6rem; text-align: left; }}
  th {{ background: #8881; }}
  tr:first-child td {{ font-weight: 600; }}
  .num {{ text-align: right; font-variant-numeric: tabular-nums; }}
  .muted {{ color: #888; font-size: .85rem; }}
  code {{ background: #8882; padding: .1rem .3rem; border-radius: 3px; font-size: .85em; }}
  .badge {{ font-size: .72rem; padding: .1rem .4rem; border-radius: 8px; background: #8883; }}
  .fab {{ color: #b23; }}
  .best {{ font-weight: 700; }}
  footer {{ margin-top: 2.5rem; font-size: .8rem; color: #888; border-top: 1px solid #8884; padding-top: 1rem; }}
</style>
</head>
<body>
<h1>AusLawExam-Bench &middot; Leaderboard</h1>
<p class="muted">{subtitle}</p>
{leaderboard}
{pairwise}
{bydifficulty}
<footer>
  <p><strong>Method.</strong> {method}</p>
  <p><strong>Contamination control.</strong> {contamination}</p>
  <p><strong>Provenance.</strong> {provenance}</p>
  <p class="muted">Run <code>{run_id}</code> &middot; {models} models &middot; {nq} questions &middot; {timestamp}</p>
</footer>
</body>
</html>
"""


def _esc(x: Any) -> str:
    return html.escape(str(x))


def _leaderboard_table(report: dict[str, Any]) -> str:
    rows = []
    best = report["models"][0]["model"] if report["models"] else None
    for m in report["models"]:
        sc = m["mean_item_score_100"]
        fr = m["fabricated_rate"]
        rank = report["models"].index(m)
        name = f'<span class="best">{_esc(m["model"])}</span>' if m["model"] == best else _esc(m["model"])
        mock = ' <span class="badge">mock</span>' if m.get("is_mock") else ""
        rows.append(
            f"<tr><td>{rank + 1}</td><td>{name}{mock}</td>"
            f"<td class='num'>{sc['point']:.1f} [{sc['ci95'][0]:.1f}, {sc['ci95'][1]:.1f}]</td>"
            f"<td class='num fab'>{fr['point']:.3f} [{fr['ci95'][0]:.3f}, {fr['ci95'][1]:.3f}]</td>"
            f"<td class='num'>{m['n_questions']}</td></tr>"
        )
    return (
        "<h2>Item score (0&ndash;100) &amp; fabricated-citation rate</h2>"
        "<table><thead><tr><th>#</th><th>Model</th>"
        "<th class='num'>Mean score (95% CI)</th>"
        "<th class='num'>Fabricated rate (95% CI)</th><th class='num'>Q</th></tr></thead>"
        "<tbody>" + "".join(rows) + "</tbody></table>"
        "<p class='muted'>Lower fabricated-citation rate is better; the headline metric "
        "for a legal benchmark is the tendency to invent authority.</p>"
    )


def _pairwise_table(report: dict[str, Any]) -> str:
    if not report.get("pairwise_permutation"):
        return ""
    rows = []
    for p in report["pairwise_permutation"]:
        sig = "**significant**" if p["significant_05"] else "n.s."
        rows.append(
            f"<tr><td>{_esc(p['a'])}</td><td>{_esc(p['b'])}</td>"
            f"<td class='num'>{p['mean_diff']:+.2f}</td><td class='num'>{p['p_value']:.4f}</td>"
            f"<td>{sig}</td></tr>"
        )
    return (
        "<h2>Pairwise significance</h2>"
        "<table><thead><tr><th>Model A</th><th>Model B</th>"
        "<th class='num'>Mean diff (A&minus;B)</th><th class='num'>p-value</th>"
        "<th>Two-sided, &alpha;=.05</th></tr></thead><tbody>"
        + "".join(rows) + "</tbody></table>"
        "<p class='muted'>Paired permutation test over the shared question set.</p>"
    )


def _difficulty_table(report: dict[str, Any]) -> str:
    # Collect the union of difficulty levels across models.
    diffs: list[str] = []
    for m in report["models"]:
        for d in m.get("per_difficulty", {}):
            if d not in diffs:
                diffs.append(d)
    if not diffs:
        return ""
    head = "<tr><th>Model</th>" + "".join(f"<th class='num'>{_esc(d)}</th>" for d in diffs) + "</tr>"
    body = []
    for m in report["models"]:
        pd = m.get("per_difficulty", {})
        cells = "".join(
            f"<td class='num'>{pd[d] if d in pd else '&mdash;'}</td>" for d in diffs
        )
        body.append(f"<tr><td>{_esc(m['model'])}</td>{cells}</tr>")
    return (
        "<h2>By difficulty</h2>"
        "<table><thead>" + head + "</thead><tbody>" + "".join(body) + "</tbody></table>"
    )


def build_leaderboard_html(
    report: dict[str, Any], *, meta: Optional[dict[str, Any]] = None
) -> str:
    meta = meta or {}
    models = [m["model"] for m in report.get("models", [])]
    mock_note = " (some slots ran as offline mocks &mdash; no API key configured)" \
        if any(m.get("is_mock") for m in report.get("models", [])) else ""
    return _PAGE.format(
        subtitle=f"A public, reproducible benchmark of Australian legal reasoning. "
                 f"{len(models)} models &middot; {report.get('n_questions_total', 0)} "
                 f"exam-style questions{mock_note}.",
        leaderboard=_leaderboard_table(report),
        pairwise=_pairwise_table(report),
        bydifficulty=_difficulty_table(report),
        method=_esc(report.get("method", {}).get("ci", "")) + " "
               + _esc(report.get("method", {}).get("comparison", "")),
        contamination=_esc(meta.get("contamination_note",
                                     "BIG-bench-style canary strings are embedded in each "
                                     "item's gold answer to detect training-data "
                                     "contamination of model outputs.")),
        provenance=_esc(meta.get("provenance_note",
                                 "Sample items are provisional and require lawyer "
                                 "verification before publication.")),
        run_id=_esc(report.get("run_id", "")),
        models=len(models),
        nq=report.get("n_questions_total", 0),
        timestamp=_esc(meta.get("finished_at", "")),
    )


def publish_site(
    out_dir: str | Path,
    *,
    report: dict[str, Any],
    meta: Optional[dict[str, Any]] = None,
) -> str:
    """Write the static site into ``out_dir`` and return the index.html path."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    index = out / "index.html"
    index.write_text(build_leaderboard_html(report, meta=meta), encoding="utf-8")
    # Ship the underlying numbers too, so the page is auditable without JS.
    (out / "stats.json").write_text(
        json.dumps(report, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    return str(index)
