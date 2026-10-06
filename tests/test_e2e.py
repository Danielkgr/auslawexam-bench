"""Mock-only end-to-end integration: run -> score -> stats -> report."""

from __future__ import annotations

from pathlib import Path

from conftest import sample_items

from auslex.config import ModelSpec
from auslex.run.orchestrator import RunConfig, run
from auslex.score.score import score_run
from auslex.stats.report import build_report, render_markdown, write_report


def _mock_spec(name: str, quality: float, fab: float) -> ModelSpec:
    return ModelSpec(
        name=name,
        vendor="local",
        model=f"mock-{name}",
        runner="mock",
        mock_quality=quality,
        mock_fabricate_rate=fab,
    )


def test_full_mock_pipeline(tmp_path):
    items = sample_items()
    models = [
        _mock_spec("alpha", 0.86, 0.08),
        _mock_spec("beta", 0.60, 0.25),
    ]
    cfg = RunConfig(
        models=models,
        items=items,
        n_reps=2,
        run_id="test-run",
        out_root=tmp_path,
        base_seed=0,
    )
    rep = run(cfg)

    # --- run layer -------------------------------------------------------- #
    assert rep.n_ok == 2 * len(items) * 2  # 2 models * 2 items * 2 reps
    assert rep.n_error == 0
    run_dir = Path(rep.run_dir)
    assert (run_dir / "records.jsonl").exists()
    assert (run_dir / "meta.json").exists()
    assert (run_dir / "raw").exists()
    meta = (run_dir / "meta.json").read_text()
    assert "test-run" in meta

    # --- score layer ------------------------------------------------------ #
    srep = score_run(run_dir, items, out_root=tmp_path)
    assert srep.n_scored == rep.n_ok
    assert len(srep.models) == 2
    scored = Path(srep.scores_dir) / "scored.jsonl"
    assert scored.exists()
    n_lines = len([line for line in scored.read_text().splitlines() if line.strip()])
    assert n_lines == rep.n_ok
    # Higher-quality mock should outscore the weaker one.
    scores = {m.model: m.mean_item_score_100 for m in srep.models}
    assert scores["alpha"] > scores["beta"]

    # --- stats layer ------------------------------------------------------ #
    report = build_report(scored, run_id="test-run", n_boot=200, n_perm=200, seed=0)
    assert report["n_models"] == 2
    assert report["n_questions_total"] == len(items)
    assert len(report["pairwise_permutation"]) == 1  # 2 models -> 1 pair
    pair = report["pairwise_permutation"][0]
    assert set(pair.keys()) >= {"a", "b", "p_value", "significant_05"}

    # --- markdown + report write ------------------------------------------ #
    md = render_markdown(report)
    assert "Leaderboard" in md
    assert "alpha" in md and "beta" in md
    paths = write_report(report, tmp_path)
    assert Path(paths["stats_json"]).exists()
    assert Path(paths["report_md"]).exists()


def test_scoring_leaves_out_completions_for_changed_items(tmp_path):
    """A completion answered the prompt it was given; if the item text later
    changes, it must not be marked against the new answer key."""
    items = sample_items()
    cfg = RunConfig(
        models=[_mock_spec("alpha", 0.86, 0.08)],
        items=items,
        n_reps=2,
        run_id="stale-run",
        out_root=tmp_path,
        base_seed=0,
    )
    rep = run(cfg)
    edited = [dict(items[0], question_text="A different question."), items[1]]
    srep = score_run(Path(rep.run_dir), edited, out_root=tmp_path)
    assert srep.n_stale == 2
    assert srep.stale_items == [items[0]["id"]]
    assert srep.n_scored == 2
