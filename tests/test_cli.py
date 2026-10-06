"""Smoke tests for the CLI entry point."""

from __future__ import annotations

import pytest

from auslex.cli import ROOT, main


def test_help_exits_zero(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["--help"])
    assert exc.value.code == 0
    out = capsys.readouterr().out
    assert "auslex" in out


def test_version_exits_zero(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0
    assert "auslex" in capsys.readouterr().out


def test_validate_shipped_dataset_zero(capsys):
    questions = ROOT / "data" / "questions" / "auslex.jsonl"
    assert questions.exists()
    rc = main(["validate", "--questions", str(questions)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "errors=0" in out


def test_validate_missing_file_nonzero():
    with pytest.raises(SystemExit) as exc:
        main(["validate", "--questions", "/nonexistent/nowhere.jsonl"])
    assert exc.value.code != 0


def _bare_item(**over):
    """An item as an author might hand it over: no id and no canary yet."""
    from conftest import make_item

    item = make_item(**over)
    item.pop("id")
    item.pop("canary")
    return item


def test_import_jsonl_assigns_ids_and_canaries(tmp_path, capsys):
    import json

    src = tmp_path / "in.jsonl"
    src.write_text(json.dumps(_bare_item()) + "\n", encoding="utf-8")
    out = tmp_path / "out.jsonl"
    assert main(["import", "--input", str(src), "--out", str(out)]) == 0
    from auslex.canary import make_canary
    from auslex.io import read_jsonl

    [item] = read_jsonl(out)
    assert item["id"].startswith("auslex-") and item["id"].endswith("-0001")
    assert item["canary"] == make_canary(item["id"])


def test_import_csv_is_detected_from_the_extension(tmp_path):
    src = tmp_path / "in.csv"
    src.write_text(
        "question,answer,type,jurisdiction,area,difficulty,marks,authorities,rubric\n"
        '"What is the rule?","The rule is X.",short_answer,Cth,contract,pass,10,'
        '"Corporations Act 2001 (Cth) s 181","rule:5;application:5"\n',
        encoding="utf-8",
    )
    out = tmp_path / "out.jsonl"
    assert main(["import", "--input", str(src), "--out", str(out)]) == 0
    from auslex.io import read_jsonl

    [item] = read_jsonl(out)
    assert item["required_authorities"][0]["kind"] == "statute"


def test_run_writes_every_output_under_out_root_and_applies_config(tmp_path):
    import json

    cfg = tmp_path / "slots.json"
    cfg.write_text(json.dumps({"models": {"gpt": {"model": "gpt-from-config"}}}))
    out = tmp_path / "out"
    rc = main(["run", "--models", "gpt", "--mock", "--reps", "1", "--run-id", "t1",
               "--n-boot", "50", "--n-perm", "50", "--config", str(cfg), "--out-root", str(out)])
    assert rc == 0
    for sub in ("runs", "scores", "stats", "site"):
        assert (out / sub / "t1").is_dir(), sub
    meta = json.loads((out / "runs" / "t1" / "meta.json").read_text())
    assert meta["models"][0]["model"] == "gpt-from-config"
    # Nothing was written into the repository.
    assert not (ROOT / "stats" / "t1").exists() and not (ROOT / "site" / "t1").exists()


def test_hash_lock_catches_an_edit_after_locking(tmp_path, capsys):
    import json

    from conftest import sample_items

    q = tmp_path / "set.jsonl"
    q.write_text("".join(json.dumps(it) + "\n" for it in sample_items()), encoding="utf-8")
    assert main(["validate", "--questions", str(q), "--lock"]) == 0
    assert (tmp_path / "set.manifest.json").exists()
    assert main(["validate", "--questions", str(q)]) == 0

    items = [json.loads(line) for line in q.read_text().splitlines()]
    assert all(it["verification"]["hash"] for it in items)
    items[0]["gold_answer"] += " An unreviewed edit."
    q.write_text("".join(json.dumps(it) + "\n" for it in items), encoding="utf-8")
    capsys.readouterr()
    assert main(["validate", "--questions", str(q)]) == 1
    out = capsys.readouterr().out
    assert "HASH_MISMATCH" in out and "STALE_HASH" in out


def test_shipped_dataset_matches_its_committed_manifest():
    from auslex.ingest.validate import check_lock, check_stamps, load_manifest
    from auslex.io import read_jsonl

    items = read_jsonl(ROOT / "data" / "questions" / "auslex.jsonl")
    manifest = load_manifest(ROOT / "data" / "gold" / "manifest.json")
    assert check_lock(items, manifest) == [] and check_stamps(items) == []
    assert all(it["verification"].get("hash") for it in items)
