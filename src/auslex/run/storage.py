"""Append-only, content-hash-addressed storage for run outputs.

A run lives in ``runs/<run-id>/``:

- ``meta.json``       — immutable config snapshot (models, item hashes, seeds,
  prompt template version, git/python versions, canary). Written once at start
  and finalised at end.
- ``records.jsonl``   — the canonical append-only log: one JSON line per
  completion (the auditable record scoring consumes). Never rewritten.
- ``raw/<model>/<item-id>/rep_NN.json`` — the full raw response (including the
  exact provider payload) for each completion, addressed by item id and the
  rep. Published verbatim with the benchmark.

Nothing in a run directory is ever edited in place: every new completion is a
new append, so the run is a permanent, replayable transcript.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class RunStore:
    def __init__(self, root: str | Path, run_id: str):
        self.root = Path(root)
        self.run_dir = self.root / run_id
        self.meta_path = self.run_dir / "meta.json"
        self.records_path = self.run_dir / "records.jsonl"
        self.raw_dir = self.run_dir / "raw"
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        # Ensure the append-only log exists (empty if fresh).
        if not self.records_path.exists():
            self.records_path.touch()

    # -- config snapshot -------------------------------------------------- #
    def write_meta(self, meta: dict[str, Any]) -> None:
        with open(self.meta_path, "w", encoding="utf-8") as fh:
            json.dump(meta, fh, indent=2, sort_keys=True, default=str)
            fh.write("\n")

    def read_meta(self) -> dict[str, Any]:
        with open(self.meta_path, "r", encoding="utf-8") as fh:
            return json.load(fh)

    # -- append-only record log ------------------------------------------- #
    def log(self, record: dict[str, Any]) -> None:
        with open(self.records_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, sort_keys=True, default=str) + "\n")
            fh.flush()

    def records(self) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        if not self.records_path.exists():
            return out
        with open(self.records_path, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    out.append(json.loads(line))
        return out

    # -- raw per-completion files ----------------------------------------- #
    def write_raw(self, model: str, item_id: str, rep: int, payload: dict[str, Any]) -> Path:
        d = self.raw_dir / model / item_id
        d.mkdir(parents=True, exist_ok=True)
        p = d / f"rep_{rep:02d}.json"
        with open(p, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2, sort_keys=True, default=str)
            fh.write("\n")
        return p

    def list_runs(self) -> list[str]:
        if not self.root.exists():
            return []
        return sorted(p.name for p in self.root.iterdir() if p.is_dir())
