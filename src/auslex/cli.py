"""Command-line interface for AusLawExam-Bench.

Commands
--------
    author      Regenerate the provisional sample question set.
    validate    Validate a questions file (schema + jurisdiction + canary + dedup),
                and optionally hash-lock the gold set.
    probe-local Probe the local OpenAI-compatible endpoint and list its models.
    run         Full end-to-end pipeline: run -> score -> stats -> leaderboard site.
    score       Re-score an existing run directory.
    stats       Rebuild the statistics report for a run.
    site        Publish the leaderboard site for a run.
    export-hf   Offline Hugging Face dataset export of the question set.

The canonical demo is::

    auslex run --reps 3
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Optional

# Repo root (src/auslex/cli.py -> parents[2] == project root).
ROOT = Path(__file__).resolve().parents[2]

from .canary import GLOBAL_CANARY  # noqa: E402
from .config import load_models  # noqa: E402
from .io import read_jsonl  # noqa: E402
from .publish import build_hf_export, publish_site  # noqa: E402
from .run.orchestrator import RunConfig, probe_local, run  # noqa: E402
from .run.storage import RunStore  # noqa: E402
from .score.score import score_run  # noqa: E402
from .stats.report import (  # noqa: E402
    build_report,
    render_markdown,
    write_report,
)


def _default_questions() -> Path:
    return ROOT / "data" / "questions" / "auslex.jsonl"


def _load_items(path: str | Path) -> list[dict[str, Any]]:
    p = Path(path)
    if not p.exists():
        sys.exit(f"error: questions file not found: {p}\n"
                 f"Run `auslex author` to generate the provisional sample set.")
    return read_jsonl(p)


def _filter_models(names: Optional[str]) -> list:
    specs = load_models()
    if not names:
        return specs
    wanted = [n.strip() for n in names.split(",") if n.strip()]
    by = {s.name: s for s in specs}
    out, unknown = [], []
    for w in wanted:
        if w in by:
            out.append(by[w])
        else:
            unknown.append(w)
    if unknown:
        sys.exit(f"error: unknown model slot(s) {unknown}; "
                 f"available: {sorted(by)}")
    return out


def _print_models(specs) -> None:
    from .config import is_real
    for s in specs:
        tag = "real" if is_real(s) else "mock-fallback"
        extra = f"  [{s.base_url}]" if s.base_url else ""
        print(f"  - {s.name:<7} {s.model:<28} {tag}{extra}")


# --------------------------------------------------------------------------- #
# Subcommands
# --------------------------------------------------------------------------- #


def cmd_author(_args: argparse.Namespace) -> int:
    script = ROOT / "tools" / "author_samples.py"
    print(f"Authoring provisional sample set: {script}")
    return subprocess.call([sys.executable, str(script)])


def cmd_validate(args: argparse.Namespace) -> int:
    from .ingest import validate_dataset
    from .ingest.validate import lock_items

    items = _load_items(args.questions)
    report = validate_dataset(items)
    errs = [i for i in report.issues if i.level == "error"]
    warns = [i for i in report.issues if i.level == "warning"]
    print(f"questions file: {args.questions}")
    print(f"items={len(items)}  errors={len(errs)}  warnings={len(warns)}")
    for i in warns:
        print(f"  warn  [{i.code}] {i.item_id}: {i.message}")
    for i in errs:
        print(f"  ERROR [{i.code}] {i.item_id}: {i.message}")

    if args.lock:
        manifest = lock_items(items, ROOT / "data" / "gold" / "manifest.json")
        # Persist the hash-locked gold set.
        from .io import write_jsonl
        gold = ROOT / "data" / "gold" / "auslex.jsonl"
        write_jsonl(gold, items)
        print(f"locked gold set -> {gold}")
        print(f"manifest        -> {ROOT / 'data' / 'gold' / 'manifest.json'}")
        print(f"global canary   -> {manifest['global_canary']}")

    return 1 if errs else 0


def cmd_probe_local(args: argparse.Namespace) -> int:
    from .config import DEFAULT_LOCAL_BASE_URL
    url = args.url or DEFAULT_LOCAL_BASE_URL
    ok = probe_local(url, timeout=args.timeout)
    print(f"local endpoint: {url}")
    print(f"reachable:      {ok}")
    if ok and args.list:
        import urllib.request
        try:
            with urllib.request.urlopen(url.rstrip("/") + "/models",
                                        timeout=args.timeout) as r:
                data = json.loads(r.read().decode("utf-8"))
            models = data.get("data", data if isinstance(data, list) else [])
            print(f"models ({len(models)}):")
            for m in models:
                name = m.get("id") if isinstance(m, dict) else m
                print(f"  - {name}")
        except Exception as exc:  # pragma: no cover - network detail
            print(f"(could not list models: {exc})")
    return 0 if ok else 1


def _run_pipeline(args: argparse.Namespace) -> str:
    """Execute run -> (score -> stats -> site). Returns the run_id."""
    items = _load_items(args.questions)
    specs = _filter_models(getattr(args, "models", None))

    print("== auslex run =======================================================")
    print(f"questions : {args.questions}  ({len(items)} items)")
    print(f"models    :")
    _print_models(specs)
    print(f"reps      : {args.reps}")
    print(f"out root  : {args.out_root}")
    print()

    cfg = RunConfig(
        models=specs,
        items=items,
        n_reps=args.reps,
        run_id=args.run_id,
        out_root=Path(args.out_root),
        base_seed=args.seed,
    )
    rep = run(cfg)
    print(f"run complete: {rep.run_id}")
    print(f"  run dir : {rep.run_dir}")
    print(f"  ok={rep.n_ok}  error={rep.n_error}  completions={rep.n_completions}")
    for m in rep.models:
        flag = " [mock]" if m.is_mock else ""
        fb = " [fallback]" if m.fallback else ""
        print(f"  - {m.name:<7} ok={m.n_ok} err={m.n_error}{flag}{fb}")
    print()

    if args.no_score:
        return rep.run_id

    # Score.
    srep = score_run(rep.run_dir, items)
    print(f"scored: {srep.n_scored} completions -> {srep.scores_dir}")
    print(f"  leaderboard (mean item score / fabricated-citation rate):")
    for m in srep.models:
        flag = " [mock]" if m.is_mock else ""
        print(f"  - {m.model:<7} score={m.mean_item_score_100:5.1f}  "
              f"fab={m.fabricated_rate:.3f}  on_point={m.on_point_rate:.3f}{flag}")
    print()

    if args.no_stats:
        return rep.run_id

    # Stats + report.
    scored = Path(srep.scores_dir) / "scored.jsonl"
    report = build_report(scored, run_id=rep.run_id,
                          n_boot=args.n_boot, n_perm=args.n_perm, seed=args.seed)
    paths = write_report(report, ROOT)
    print(f"stats   : {paths['stats_json']}")
    print(f"report  : {paths['report_md']}")
    print()

    # Publish the leaderboard site.
    store = RunStore(Path(args.out_root), rep.run_id)
    meta = store.read_meta()
    meta["contamination_note"] = (
        f"Every item embeds the global canary {GLOBAL_CANARY} plus a per-item "
        "canary derived from its id; reproducing either verbatim flags "
        "training-data contamination.")
    site_dir = ROOT / "site" / rep.run_id
    index = publish_site(site_dir, report=report, meta=meta)
    print(f"site    : {index}")
    print()
    print("---- leaderboard (markdown) ----------------------------------------")
    print(render_markdown(report))
    return rep.run_id


def cmd_run(args: argparse.Namespace) -> int:
    return _run_pipeline(args)


def _resolve_run_dir(run_dir: str) -> Path:
    p = Path(run_dir)
    if not p.exists():
        # Allow passing just the run id under the default out root.
        alt = ROOT / "runs" / run_dir
        if alt.exists():
            p = alt
        else:
            sys.exit(f"error: run directory not found: {run_dir}")
    return p


def cmd_score(args: argparse.Namespace) -> int:
    run_dir = _resolve_run_dir(args.run_dir)
    items = _load_items(args.questions)
    srep = score_run(run_dir, items)
    print(f"scored: {srep.n_scored} completions -> {srep.scores_dir}")
    for m in srep.models:
        flag = " [mock]" if m.is_mock else ""
        print(f"  - {m.model:<7} score={m.mean_item_score_100:5.1f}  "
              f"fab={m.fabricated_rate:.3f}{flag}")
    return 0


def cmd_stats(args: argparse.Namespace) -> int:
    run_dir = _resolve_run_dir(args.run_dir)
    run_id = run_dir.name
    scored = ROOT / "scores" / run_id / "scored.jsonl"
    if not scored.exists():
        sys.exit(f"error: no scored.jsonl at {scored}; run `auslex score {args.run_dir}` first.")
    report = build_report(scored, run_id=run_id,
                          n_boot=args.n_boot, n_perm=args.n_perm, seed=args.seed)
    paths = write_report(report, ROOT)
    print(f"stats : {paths['stats_json']}")
    print(f"report: {paths['report_md']}")
    print()
    print(render_markdown(report))
    return 0


def cmd_site(args: argparse.Namespace) -> int:
    run_dir = _resolve_run_dir(args.run_dir)
    run_id = run_dir.name
    scored = ROOT / "scores" / run_id / "scored.jsonl"
    if not scored.exists():
        sys.exit(f"error: no scored.jsonl at {scored}; run `auslex score {args.run_dir}` first.")
    report = build_report(scored, run_id=run_id, seed=args.seed)
    store = RunStore(run_dir.parent, run_id)
    meta = store.read_meta()
    meta["contamination_note"] = (
        f"Every item embeds the global canary {GLOBAL_CANARY} plus a per-item "
        "canary derived from its id; reproducing either verbatim flags "
        "training-data contamination.")
    index = publish_site(ROOT / "site" / run_id, report=report, meta=meta)
    print(f"site: {index}")
    return 0


def cmd_export_hf(args: argparse.Namespace) -> int:
    items = _load_items(args.questions)
    out = Path(args.out)
    # build_hf_export writes questions.jsonl, README.md, dataset_info.json into `out`.
    exp = build_hf_export(out, items, name="auslex", version="0.1.0")
    print(f"exported {exp.n_items} items -> {out}")
    print(f"  files: {', '.join(exp.files)}")
    print(f"  license: cc-by-4.0 (see {out / 'README.md'})")
    return 0


# --------------------------------------------------------------------------- #
# Parser
# --------------------------------------------------------------------------- #


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="auslex",
        description="AusLawExam-Bench: a reproducible benchmark of Australian legal reasoning.",
    )
    p.add_argument("--version", action="version", version="auslex 0.1.0")
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("author", help="regenerate the provisional sample question set")
    sp.set_defaults(func=cmd_author)

    sp = sub.add_parser("validate", help="validate a questions file (and optionally lock)")
    sp.add_argument("--questions", default=str(_default_questions()))
    sp.add_argument("--lock", action="store_true",
                    help="compute + persist the hash-locked gold set and manifest")
    sp.set_defaults(func=cmd_validate)

    sp = sub.add_parser("probe-local", help="probe the local OpenAI-compatible endpoint")
    sp.add_argument("--url", default=None)
    sp.add_argument("--timeout", type=float, default=8.0)
    sp.add_argument("--list", action="store_true", help="list available models")
    sp.set_defaults(func=cmd_probe_local)

    def add_run_opts(sp: argparse.ArgumentParser, with_pipeline: bool) -> None:
        sp.add_argument("--questions", default=str(_default_questions()))
        sp.add_argument("--models", default=None,
                        help="comma-separated subset, e.g. 'local,gpt'")
        sp.add_argument("--reps", type=int, default=3)
        sp.add_argument("--seed", type=int, default=0)
        sp.add_argument("--out-root", default=str(ROOT / "runs"))
        sp.add_argument("--run-id", default=None)
        sp.add_argument("--n-boot", type=int, default=10_000)
        sp.add_argument("--n-perm", type=int, default=10_000)
        if with_pipeline:
            sp.add_argument("--no-score", action="store_true")
            sp.add_argument("--no-stats", action="store_true")

    sp = sub.add_parser("run", help="full end-to-end pipeline (run->score->stats->site)")
    add_run_opts(sp, with_pipeline=True)
    sp.set_defaults(func=cmd_run)

    sp = sub.add_parser("score", help="re-score an existing run directory")
    sp.add_argument("run_dir")
    sp.add_argument("--questions", default=str(_default_questions()))
    sp.set_defaults(func=cmd_score)

    sp = sub.add_parser("stats", help="rebuild the statistics report for a run")
    sp.add_argument("run_dir")
    sp.add_argument("--n-boot", type=int, default=10_000)
    sp.add_argument("--n-perm", type=int, default=10_000)
    sp.add_argument("--seed", type=int, default=0)
    sp.set_defaults(func=cmd_stats)

    sp = sub.add_parser("site", help="publish the leaderboard site for a run")
    sp.add_argument("run_dir")
    sp.add_argument("--seed", type=int, default=0)
    sp.set_defaults(func=cmd_site)

    sp = sub.add_parser("export-hf", help="offline Hugging Face dataset export")
    sp.add_argument("--questions", default=str(_default_questions()))
    sp.add_argument("--out", default=str(ROOT / "export" / "hf"))
    sp.set_defaults(func=cmd_export_hf)

    return p


def main(argv: Optional[list[str]] = None) -> int:
    args = _build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
