"""Command-line interface for AusLawExam-Bench.

Commands
--------
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
import datetime as dt
import json
import sys
from pathlib import Path
from typing import Any

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
        sys.exit(f"error: questions file not found: {p}")
    return read_jsonl(p)


# --------------------------------------------------------------------------- #
# Import helper
# --------------------------------------------------------------------------- #


def _parse_csv_row(row: dict[str, str]) -> dict[str, Any]:
    """Map a CSV row (columns: question,answer,type,jurisdiction,area,difficulty,
    marks,authorities,rubric[,options,correct]) to a QuestionItem dict."""
    # Strip whitespace from all values (CSV may emit None keys for extra columns).
    cleaned: dict[str, str] = {}
    for k, v in row.items():
        if k is None:
            continue
        cleaned[k.strip()] = v.strip() if v is not None else ""

    def _split(v: str, sep: str = ";") -> list[str]:
        if not v:
            return []
        return [x.strip() for x in v.split(sep) if x.strip()]

    juris = _split(cleaned.get("jurisdiction", "Cth"), sep=",")
    authorities_raw = _split(cleaned.get("authorities", ""))
    authorities = []
    for a in authorities_raw:
        # Try to detect kind: "Act ... (Cth) s N" -> statute, otherwise case.
        if "Act" in a and "s " in a:
            kind = "statute"
        else:
            kind = "case"
        authorities.append({"kind": kind, "cite": a})

    rubric_raw = _split(cleaned.get("rubric", ""))
    rubric = []
    for r in rubric_raw:
        # Support both "criterion:max" and "criterion(max)" formats.
        if "(" in r and r.endswith(")"):
            crit, max_str = r.rsplit("(", 1)
            max_val = int(max_str.rstrip(")"))
        elif ":" in r:
            crit, max_str = r.split(":", 1)
            max_val = int(max_str.strip())
        else:
            crit = r
            max_val = 1
        rubric.append({"criterion": crit.strip(), "max": max_val})

    item: dict[str, Any] = {
        "type": cleaned.get("type", "short_answer"),
        "jurisdiction": juris,
        "priestley_area": cleaned.get("area", "contract"),
        "difficulty": cleaned.get("difficulty", "pass"),
        "marks": int(cleaned.get("marks", 10)),
        "question_text": cleaned.get("question", ""),
        "gold_answer": cleaned.get("answer", ""),
        "topics": _split(cleaned.get("topics", cleaned.get("area", ""))),
        "key_issues": _split(cleaned.get("key_issues", "")),
        "required_authorities": authorities,
        "rubric": rubric,
        "law_as_at": cleaned.get("law_as_at", "2026-01-01"),
        "provenance": {"author": "imported", "provisional": True, "tier": "C"},
        "verification": {"second_pass": False},
        "version": "0.1.0",
    }

    # MCQ fields.
    if item["type"] == "mcq":
        options_raw = cleaned.get("options", "")
        if options_raw:
            # Accept comma-separated or semicolon-separated options with letter prefixes.
            import re

            raw_options = re.findall(r"[A-D]\.\s*([^,;]+)", options_raw)
            if not raw_options:
                raw_options = _split(options_raw)
            item["mcq_options"] = [o.strip() for o in raw_options if o.strip()]
        correct = cleaned.get("correct", cleaned.get("mcq_correct", ""))
        if correct:
            idx = ord(correct.upper()) - ord("A")
            if 0 <= idx < 26:
                item["mcq_correct"] = idx

    return item


def cmd_import(args: argparse.Namespace) -> int:
    """Import questions from an external file (JSONL or CSV)."""
    import csv as _csv

    from .canary import make_canary

    inp = Path(args.input)
    if not inp.exists():
        sys.exit(f"error: input file not found: {inp}")

    fmt = args.format or ("csv" if inp.suffix.lower() == ".csv" else "jsonl")
    items: list[dict[str, Any]] = []
    year = dt.datetime.now(dt.timezone.utc).strftime("%Y")

    if fmt == "csv":
        with open(inp, encoding="utf-8") as fh:
            reader = _csv.DictReader(fh)
            for row in reader:
                try:
                    item = _parse_csv_row(row)
                    # Generate id and canary for imported items.
                    if "id" not in item:
                        item["id"] = f"auslex-{year}-{len(items) + 1:04d}"
                    if "canary" not in item:
                        item["canary"] = make_canary(item["id"])
                    items.append(item)
                except (ValueError, KeyError) as exc:
                    print(f"  warn  [PARSE] row {len(items) + 1}: {exc}")
    else:
        # JSONL — each line is either a full item or a dict missing id/canary.
        for line in read_jsonl(inp):
            if "id" not in line or not line["id"].startswith("auslex-"):
                line["id"] = f"auslex-{year}-{len(items) + 1:04d}"
            if "canary" not in line or not line["canary"].startswith("auslex:"):
                line["canary"] = make_canary(line["id"])
            line.setdefault("version", "0.1.0")
            line.setdefault("provenance", {}).setdefault("provisional", True)
            items.append(line)

    # Validation.
    from .ingest import validate_dataset

    report = validate_dataset(items)
    errs = [i for i in report.issues if i.level == "error"]
    warns = [i for i in report.issues if i.level == "warning"]
    print(f"imported  : {len(items)} items from {inp}")
    print(f"validated : errors={len(errs)}  warnings={len(warns)}")
    for i in warns:
        print(f"  warn  [{i.code}] {i.item_id}: {i.message}")
    for i in errs:
        print(f"  ERROR [{i.code}] {i.item_id}: {i.message}")

    if errs:
        print("validation failed — not writing output (use --dry-run to preview)")
        return 1

    if args.dry_run:
        print("\n--- dry-run: would write the following items ---")
        for it in items:
            print(f"  - {it['id']}  ({it.get('type')})  {it.get('marks')} marks")
        return 0

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    from .io import write_jsonl

    write_jsonl(out, items)
    print(f"written   : {out}  ({len(items)} items)")
    return 0


def _filter_models(names: str | None, config: str | None = None) -> list:
    specs = load_models(config)
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
        sys.exit(f"error: unknown model slot(s) {unknown}; available: {sorted(by)}")
    return out


def _print_models(specs) -> None:
    from .config import is_real

    for s in specs:
        if is_real(s):
            tag = "real"
        elif s.runner == "mock":
            tag = "mock (explicit)"
        else:
            tag = "skip (no key)"
        extra = f"  [{s.base_url}]" if s.base_url else ""
        print(f"  - {s.name:<7} {s.model:<28} {tag}{extra}")


# --------------------------------------------------------------------------- #
# Subcommands
# --------------------------------------------------------------------------- #


def _manifest_path(questions: Path) -> Path:
    """The default dataset's manifest lives in data/gold; others sit beside the file."""
    if questions.resolve() == _default_questions().resolve():
        return ROOT / "data" / "gold" / "manifest.json"
    return questions.with_suffix(".manifest.json")


def cmd_validate(args: argparse.Namespace) -> int:
    from .ingest import validate_dataset
    from .ingest.validate import check_lock, check_stamps, load_manifest, lock_items
    from .io import write_jsonl

    questions = Path(args.questions)
    manifest_path = Path(args.manifest) if args.manifest else _manifest_path(questions)
    items = _load_items(questions)
    report = validate_dataset(items)
    if args.lock:
        if report.errors:
            print("not locking: the dataset has validation errors")
        else:
            manifest = lock_items(items, manifest_path)
            write_jsonl(questions, items, sort_keys=True)
            print(f"locked {len(items)} items -> {manifest_path}")
            print(f"global canary   -> {manifest['global_canary']}")
    if manifest_path.exists():
        report.issues += check_lock(items, load_manifest(manifest_path))
        report.issues += check_stamps(items)
    else:
        print(f"no manifest at {manifest_path}; run with --lock to create one")

    errs = [i for i in report.issues if i.level == "error"]
    warns = [i for i in report.issues if i.level == "warning"]
    print(f"questions file: {questions}")
    print(f"items={len(items)}  errors={len(errs)}  warnings={len(warns)}")
    for i in warns:
        print(f"  warn  [{i.code}] {i.item_id}: {i.message}")
    for i in errs:
        print(f"  ERROR [{i.code}] {i.item_id}: {i.message}")
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
            with urllib.request.urlopen(url.rstrip("/") + "/models", timeout=args.timeout) as r:
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
    specs = _filter_models(getattr(args, "models", None), getattr(args, "config", None))

    print("== auslex run =======================================================")
    print(f"questions : {args.questions}  ({len(items)} items)")
    print("models    :")
    _print_models(specs)
    print(f"reps      : {args.reps}")
    print(f"out root  : {args.out_root}")
    print()

    cfg = RunConfig(
        models=specs,
        items=items,
        n_reps=args.reps,
        run_id=args.run_id,
        out_root=Path(args.out_root) / "runs",
        base_seed=args.seed,
        allow_mock_fallback=getattr(args, "mock", False),
        concurrency=args.concurrency,
        max_retries=args.max_retries,
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
    out_root = Path(args.out_root)
    srep = score_run(rep.run_dir, items, out_root=out_root / "scores")
    print(f"scored: {srep.n_scored} completions -> {srep.scores_dir}")
    print("  leaderboard (mean item score / fabricated-citation rate):")
    for ms in srep.models:
        flag = " [mock]" if ms.is_mock else ""
        print(
            f"  - {ms.model:<7} score={ms.mean_item_score_100:5.1f}  "
            f"fab={ms.fabricated_rate:.3f}  on_point={ms.on_point_rate:.3f}{flag}"
        )
    print()

    if args.no_stats:
        return rep.run_id

    # Stats + report.
    scored = Path(srep.scores_dir) / "scored.jsonl"
    report = build_report(
        scored, run_id=rep.run_id, n_boot=args.n_boot, n_perm=args.n_perm, seed=args.seed
    )
    paths = write_report(report, out_root)
    print(f"stats   : {paths['stats_json']}")
    print(f"report  : {paths['report_md']}")
    print()

    # Publish the leaderboard site.
    store = RunStore(out_root / "runs", rep.run_id)
    meta = store.read_meta()
    meta["contamination_note"] = (
        f"Every item embeds the global canary {GLOBAL_CANARY} plus a per-item "
        "canary derived from its id; reproducing either verbatim flags "
        "training-data contamination."
    )
    site_dir = out_root / "site" / rep.run_id
    index = publish_site(site_dir, report=report, meta=meta)
    print(f"site    : {index}")
    print()
    print("---- leaderboard (markdown) ----------------------------------------")
    print(render_markdown(report))
    return rep.run_id


def cmd_run(args: argparse.Namespace) -> int:
    _run_pipeline(args)
    return 0


def _resolve_run_dir(run_dir: str, out_root: str | None = None) -> Path:
    p = Path(run_dir)
    if not p.exists():
        # Allow passing just the run id under the output root.
        alt = Path(out_root or ROOT) / "runs" / run_dir
        if alt.exists():
            p = alt
        else:
            sys.exit(f"error: run directory not found: {run_dir}")
    return p


def _output_root(args: argparse.Namespace, run_dir: Path) -> Path:
    """The folder holding runs/, scores/, stats/, and site/ for this run."""
    if getattr(args, "out_root", None):
        return Path(args.out_root)
    return run_dir.resolve().parent.parent


def cmd_score(args: argparse.Namespace) -> int:
    run_dir = _resolve_run_dir(args.run_dir, args.out_root)
    items = _load_items(args.questions)
    srep = score_run(run_dir, items, out_root=_output_root(args, run_dir) / "scores")
    print(f"scored: {srep.n_scored} completions -> {srep.scores_dir}")
    if srep.n_stale:
        print(
            f"  left out {srep.n_stale} completions whose item text has changed since "
            f"the run: {', '.join(srep.stale_items)}"
        )
    for m in srep.models:
        flag = " [mock]" if m.is_mock else ""
        print(
            f"  - {m.model:<7} score={m.mean_item_score_100:5.1f}  "
            f"fab={m.fabricated_rate:.3f}{flag}"
        )
    return 0


def cmd_stats(args: argparse.Namespace) -> int:
    run_dir = _resolve_run_dir(args.run_dir, args.out_root)
    run_id = run_dir.name
    out_root = _output_root(args, run_dir)
    scored = out_root / "scores" / run_id / "scored.jsonl"
    if not scored.exists():
        sys.exit(f"error: no scored.jsonl at {scored}; run `auslex score {args.run_dir}` first.")
    report = build_report(
        scored, run_id=run_id, n_boot=args.n_boot, n_perm=args.n_perm, seed=args.seed
    )
    paths = write_report(report, out_root)
    print(f"stats : {paths['stats_json']}")
    print(f"report: {paths['report_md']}")
    print()
    print(render_markdown(report))
    return 0


def cmd_site(args: argparse.Namespace) -> int:
    run_dir = _resolve_run_dir(args.run_dir, args.out_root)
    run_id = run_dir.name
    out_root = _output_root(args, run_dir)
    scored = out_root / "scores" / run_id / "scored.jsonl"
    if not scored.exists():
        sys.exit(f"error: no scored.jsonl at {scored}; run `auslex score {args.run_dir}` first.")
    report = build_report(scored, run_id=run_id, seed=args.seed)
    store = RunStore(run_dir.parent, run_id)
    meta = store.read_meta()
    meta["contamination_note"] = (
        f"Every item embeds the global canary {GLOBAL_CANARY} plus a per-item "
        "canary derived from its id; reproducing either verbatim flags "
        "training-data contamination."
    )
    index = publish_site(out_root / "site" / run_id, report=report, meta=meta)
    print(f"site: {index}")
    return 0


# Mean completion length of the committed local run, auslex-2026-09-14-ornith.
DEFAULT_OUTPUT_TOKENS = 1538


def cmd_estimate(args: argparse.Namespace) -> int:
    """Print call counts and an estimated cost before a live run."""
    from .pricing import price_for
    from .prompts import build_prompt

    items = _load_items(args.questions)
    specs = _filter_models(args.models, args.config)
    overrides: dict[str, tuple[float, float]] = {}
    for entry in args.price or []:
        model, _, value = entry.partition("=")
        inp, _, out = value.partition(",")
        overrides[model] = (float(inp), float(out))

    # About four characters per token, so this is an approximation.
    prompt_tokens = sum(len("".join(build_prompt(it))) for it in items) // 4
    print("ESTIMATE ONLY.  Input tokens are approximated from prompt length at four characters")
    print("per token.  Output assumes", args.output_tokens, "tokens per answer; thinking and")
    print("reasoning tokens are billed as output and are not included, so the real cost can be")
    print("higher.  The last column assumes every answer uses its full output budget.")
    print()
    print(
        f"{'slot':<9}{'model':<24}{'calls':>6}{'input tok':>11}{'output tok':>12}"
        f"{'est. USD':>11}{'max USD':>11}"
    )
    total = 0.0
    for spec in specs:
        calls = len(items) * args.reps
        tok_in = prompt_tokens * args.reps
        tok_out = calls * args.output_tokens
        price = overrides.get(spec.model) or price_for(spec.model)
        if price is None:
            est = top = "unknown"
        else:
            cost = (tok_in * price[0] + tok_out * price[1]) / 1_000_000
            worst = (tok_in * price[0] + calls * spec.max_tokens * price[1]) / 1_000_000
            total += cost
            est, top = f"{cost:.2f}", f"{worst:.2f}"
        print(
            f"{spec.name:<9}{spec.model[:23]:<24}{calls:>6}{tok_in:>11,}{tok_out:>12,}"
            f"{est:>11}{top:>11}"
        )
    print()
    print(f"estimated total for priced slots: about USD {total:.2f}")
    unknown = [s.model for s in specs if s.model not in overrides and price_for(s.model) is None]
    if unknown:
        print(
            "no confirmed price for: "
            + ", ".join(unknown)
            + "; pass --price MODEL=IN,OUT in USD per million tokens"
        )
    return 0


def cmd_pages(args: argparse.Namespace) -> int:
    from .publish.pages import build_pages

    published = build_pages(args.out_root, args.out)
    print(f"published {len(published)} real run(s) -> {args.out}")
    for run_id in published:
        print(f"  - {run_id}")
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

    sp = sub.add_parser("validate", help="validate a questions file (and optionally lock)")
    sp.add_argument("--questions", default=str(_default_questions()))
    sp.add_argument(
        "--lock", action="store_true", help="stamp each item's content hash and write the manifest"
    )
    sp.add_argument(
        "--manifest",
        default=None,
        help="manifest path (default: data/gold/manifest.json for the shipped set)",
    )
    sp.set_defaults(func=cmd_validate)

    sp = sub.add_parser("probe-local", help="probe the local OpenAI-compatible endpoint")
    sp.add_argument("--url", default=None)
    sp.add_argument("--timeout", type=float, default=8.0)
    sp.add_argument("--list", action="store_true", help="list available models")
    sp.set_defaults(func=cmd_probe_local)

    def add_run_opts(sp: argparse.ArgumentParser, with_pipeline: bool) -> None:
        sp.add_argument("--questions", default=str(_default_questions()))
        sp.add_argument("--models", default=None, help="comma-separated subset, e.g. 'local,gpt'")
        sp.add_argument("--reps", type=int, default=3)
        sp.add_argument("--seed", type=int, default=0)
        sp.add_argument(
            "--out-root",
            default=str(ROOT),
            help="folder that receives runs/, scores/, stats/, and site/ (default: the repository)",
        )
        sp.add_argument(
            "--config",
            default=None,
            help='JSON file of per-slot overrides, e.g. {"models": {"gpt": {"model": "..."}}}',
        )
        sp.add_argument("--run-id", default=None)
        sp.add_argument("--n-boot", type=int, default=10_000)
        sp.add_argument("--n-perm", type=int, default=10_000)
        sp.add_argument(
            "--concurrency",
            type=int,
            default=4,
            help="calls in flight at once (records keep a fixed order)",
        )
        sp.add_argument(
            "--max-retries",
            type=int,
            default=2,
            help="extra attempts for rate limits, 5xx, and network errors",
        )
        sp.add_argument(
            "--mock",
            action="store_true",
            help="allow mock fallback for slots without API keys (offline testing only)",
        )
        if with_pipeline:
            sp.add_argument("--no-score", action="store_true")
            sp.add_argument("--no-stats", action="store_true")

    sp = sub.add_parser("run", help="full end-to-end pipeline (run->score->stats->site)")
    add_run_opts(sp, with_pipeline=True)
    sp.set_defaults(func=cmd_run)

    sp = sub.add_parser("score", help="re-score an existing run directory")
    sp.add_argument("run_dir")
    sp.add_argument(
        "--out-root",
        default=None,
        help="folder holding runs/, scores/, stats/, and site/ "
        "(default: two levels above the run directory)",
    )
    sp.add_argument("--questions", default=str(_default_questions()))
    sp.set_defaults(func=cmd_score)

    sp = sub.add_parser("stats", help="rebuild the statistics report for a run")
    sp.add_argument("run_dir")
    sp.add_argument(
        "--out-root",
        default=None,
        help="folder holding runs/, scores/, stats/, and site/ "
        "(default: two levels above the run directory)",
    )
    sp.add_argument("--n-boot", type=int, default=10_000)
    sp.add_argument("--n-perm", type=int, default=10_000)
    sp.add_argument("--seed", type=int, default=0)
    sp.set_defaults(func=cmd_stats)

    sp = sub.add_parser("site", help="publish the leaderboard site for a run")
    sp.add_argument("run_dir")
    sp.add_argument(
        "--out-root",
        default=None,
        help="folder holding runs/, scores/, stats/, and site/ "
        "(default: two levels above the run directory)",
    )
    sp.add_argument("--seed", type=int, default=0)
    sp.set_defaults(func=cmd_site)

    sp = sub.add_parser("estimate", help="print call counts and an estimated cost")
    sp.add_argument("--questions", default=str(_default_questions()))
    sp.add_argument("--models", default=None, help="comma-separated slots, e.g. 'claude,gpt'")
    sp.add_argument("--reps", type=int, default=3)
    sp.add_argument("--config", default=None)
    sp.add_argument(
        "--output-tokens",
        type=int,
        default=DEFAULT_OUTPUT_TOKENS,
        help="assumed answer length (default: the committed local run's mean)",
    )
    sp.add_argument(
        "--price", action="append", help="MODEL=IN,OUT in USD per million tokens; repeatable"
    )
    sp.set_defaults(func=cmd_estimate)

    sp = sub.add_parser("pages", help="build the public site from committed real runs only")
    sp.add_argument("--out", default="_site", help="output folder (default: _site)")
    sp.add_argument(
        "--out-root",
        default=str(ROOT),
        help="folder holding runs/, scores/, and stats/ (default: the repository)",
    )
    sp.set_defaults(func=cmd_pages)

    sp = sub.add_parser("export-hf", help="offline Hugging Face dataset export")
    sp.add_argument("--questions", default=str(_default_questions()))
    sp.add_argument("--out", default=str(ROOT / "export" / "hf"))
    sp.set_defaults(func=cmd_export_hf)

    sp = sub.add_parser("import", help="import questions from JSONL or CSV")
    sp.add_argument("--input", required=True, help="input file (JSONL or CSV)")
    sp.add_argument(
        "--format",
        choices=["jsonl", "csv"],
        default=None,
        help="auto-detected from extension if omitted",
    )
    sp.add_argument(
        "--out",
        default=str(ROOT / "data" / "questions" / "imported.jsonl"),
        help="output JSONL path (default: data/questions/imported.jsonl)",
    )
    sp.add_argument(
        "--dry-run", action="store_true", help="validate and report but do not write output"
    )
    sp.set_defaults(func=cmd_import)

    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
