"""The public site publishes committed real runs and never mock runs."""

from __future__ import annotations

import shutil

from conftest import sample_items

from auslex.cli import ROOT, main
from auslex.config import ModelSpec
from auslex.publish.pages import build_pages
from auslex.run.orchestrator import RunConfig, run
from auslex.score.score import score_run

REAL = "auslex-2026-09-14-ornith"


def test_pages_publish_the_real_run_and_skip_mock_runs(tmp_path):
    root = tmp_path / "root"
    for sub in ("runs", "scores", "stats"):
        shutil.copytree(ROOT / sub / REAL, root / sub / REAL)
    mock = ModelSpec(name="m", vendor="local", model="m", runner="mock")
    rep = run(
        RunConfig(
            models=[mock], items=sample_items(), n_reps=1, run_id="mock-run", out_root=root / "runs"
        )
    )
    score_run(rep.run_dir, sample_items(), out_root=root / "scores")

    out = tmp_path / "site"
    assert build_pages(root, out) == [REAL]
    index = (out / "index.html").read_text()
    assert REAL in index and "mock-run" not in index
    assert (out / REAL / "index.html").exists()
    assert not (out / "mock-run").exists()


def test_pages_command_builds_from_the_repository(tmp_path, capsys):
    assert main(["pages", "--out", str(tmp_path / "site")]) == 0
    assert REAL in capsys.readouterr().out
