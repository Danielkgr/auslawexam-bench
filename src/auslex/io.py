"""Small IO and hashing helpers shared across the harness.

Hashing is load-bearing: items are locked by content hash, and run outputs are
addressed by content hash, so everything is reproducible and tamper-evident.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable


def read_jsonl(path: str | Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def write_jsonl(path: str | Path, rows: Iterable[dict[str, Any]]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def canonical_json(obj: Any) -> str:
    """Deterministic JSON encoding (sorted keys, compact separators)."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_of(obj: Any) -> str:
    return hashlib.sha256(canonical_json(obj).encode("utf-8")).hexdigest()


def hash_item(item: dict[str, Any]) -> str:
    """Content hash of an item, excluding the volatile ``verification.hash`` field.

    The hash is what gets written into ``verification.hash`` on lock, and what a
    later ``validate`` pass compares against to detect unapproved edits.
    """
    clone = json.loads(json.dumps(item))
    ver = clone.get("verification")
    if isinstance(ver, dict):
        ver.pop("hash", None)
    return sha256_of(clone)
