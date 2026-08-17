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
