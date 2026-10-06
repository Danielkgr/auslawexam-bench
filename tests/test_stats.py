"""The reported point estimate and its interval must be the same statistic."""

from __future__ import annotations

import json

import pytest

from auslex.cli import ROOT
from auslex.config import ModelSpec
from auslex.run.orchestrator import RunConfig, run
from auslex.score.score import score_run
from auslex.stats.permutation import paired_permutation, paired_permutation_ratio
from auslex.stats.report import build_report
from conftest import sample_items


def _inside(stat: dict) -> bool:
    lo, hi = stat["ci95"]
    return lo <= stat["point"] <= hi


@pytest.fixture(scope="module")
def mock_report(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("stats")
    specs = [
        ModelSpec(name=n, vendor="local", model=n, runner="mock",
                  mock_quality=q, mock_fabricate_rate=f)
        for n, q, f in [("alpha", 0.86, 0.08), ("beta", 0.55, 0.6)]
    ]
    rep = run(RunConfig(models=specs, items=sample_items(), n_reps=3, run_id="s",
                        out_root=tmp / "runs"))
    srep = score_run(rep.run_dir, sample_items(), out_root=tmp / "scores")
    return build_report(f"{srep.scores_dir}/scored.jsonl", run_id="s", n_boot=500, n_perm=500)


def test_point_lies_inside_its_interval_on_mock_data(mock_report):
    for m in mock_report["models"]:
        assert _inside(m["mean_item_score_100"]), m
        assert _inside(m["fabricated_rate"]), m


def test_fabricated_point_is_the_pooled_rate(mock_report):
    for m in mock_report["models"]:
        fr = m["fabricated_rate"]
        assert fr["point"] == round(fr["fabricated"] / fr["citations"], 4)


def test_point_lies_inside_its_interval_on_the_committed_real_run():
    scored = ROOT / "scores" / "auslex-2026-09-14-ornith" / "scored.jsonl"
    report = build_report(scored, run_id="real", n_boot=2000, n_perm=200)
    for m in report["models"]:
        assert _inside(m["mean_item_score_100"]) and _inside(m["fabricated_rate"]), m


def test_significant_is_a_method():
    r = paired_permutation({"a": 1.0, "b": 2.0, "c": 3.0}, {"a": 0.0, "b": 1.0, "c": 2.0},
                           n_perm=100)
    assert r.significant(alpha=1.1) is True
    assert r.to_dict()["significant_05"] is r.significant(0.05)


def test_ratio_permutation_detects_a_real_difference():
    low = {f"q{i}": (0, 10) for i in range(8)}
    high = {f"q{i}": (9, 10) for i in range(8)}
    assert paired_permutation_ratio(high, low, n_perm=2000).p_value < 0.05
    same = paired_permutation_ratio(low, dict(low), n_perm=500)
    assert same.mean_diff == 0 and same.p_value == 1.0
    assert json.dumps(same.to_dict())
