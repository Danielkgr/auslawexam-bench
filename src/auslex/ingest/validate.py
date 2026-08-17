"""Dataset validation + hash-locking.

``validate`` runs every item through: schema -> jurisdiction rule -> canary
presence -> (optional) contamination. ``lock`` computes the per-item content
hash and writes ``data/gold/manifest.json``; a later ``check_lock`` detects any
edit made after the lock (the item's stored hash no longer matches), which is
exactly the tamper-evidence the design doc requires for the gold set.
"""

from __future__ import annotations

import datetime as _dt
import json
from pathlib import Path
from typing import Any, Iterable, Optional

from .. import canary as _canary
from ..io import hash_item
from ..schema import validate_item
from . import filters
from .contamination import check_against_corpus, dedup_items
from .issues import Issue, Report


def validate_item_dict(item: dict[str, Any]) -> list[Issue]:
    """Validate one item dict across schema + jurisdiction + canary."""
    issues: list[Issue] = []
    item_id = item.get("id")
    try:
        validate_item(item)
    except ValueError as exc:
        for line in str(exc).splitlines():
            issues.append(Issue("error", "SCHEMA", line.strip(), item_id))
        return issues  # schema failure short-circuits the rest

    issues += filters.check_item(item)

    c = item.get("canary", "")
    if not c.startswith("auslex:"):
        issues.append(
            Issue("error", "CANARY", "item has no valid 'auslex:' canary", item_id)
        )
    # A freshly-authored item must NOT already contain its own global canary
    # (that would mean the dataset text leaked into the item body).
    if _canary.GLOBAL_CANARY in item.get("question_text", ""):
        issues.append(
            Issue(
                "warning",
                "CANARY_IN_BODY",
                "question body contains the global canary string",
                item_id,
            )
        )
    return issues


def validate_dataset(
    items: list[dict[str, Any]],
    corpus_texts: Optional[Iterable[str]] = None,
    dedup: bool = True,
) -> Report:
    """Validate a full candidate dataset and return an aggregated Report."""
    report = Report()

    # Uniqueness of ids.
    seen: set[str] = set()
    for it in items:
        iid = it.get("id")
        if iid in seen:
            report.add(Issue("error", "DUP_ID", f"duplicate item id {iid!r}", iid))
        seen.add(iid)

    for it in items:
        report.issues += validate_item_dict(it)
        if corpus_texts is not None:
            report.issues += check_against_corpus(
                it.get("question_text", ""),
                corpus_texts,
                item_id=it.get("id"),
            )
    if dedup:
        report.issues += dedup_items(items)

    report.stats["n_items"] = len(items)
    report.stats["n_errors"] = len(report.errors)
    report.stats["n_warnings"] = len(report.warnings)
    return report


# --------------------------------------------------------------------------- #
# Hash-locking (the gold-set integrity gate)
# --------------------------------------------------------------------------- #


def _manifest_entry(item: dict[str, Any]) -> dict[str, Any]:
    h = hash_item(item)
    ver = item.get("verification", {})
    return {
        "version": item.get("version"),
        "hash": h,
        "verified_at": ver.get("verified_at"),
        "second_pass": ver.get("second_pass", False),
    }


def compute_manifest(items: list[dict[str, Any]]) -> dict[str, Any]:
    """Map item id -> {version, hash, verified_at, second_pass}."""
    return {
        "global_canary": _canary.GLOBAL_CANARY,
        "generated_at": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        "items": {it["id"]: _manifest_entry(it) for it in items if it.get("id")},
    }


def write_manifest(manifest: dict[str, Any], path: str | Path) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2, sort_keys=True)
        fh.write("\n")


def load_manifest(path: str | Path) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def lock_items(items: list[dict[str, Any]], manifest_path: str | Path) -> dict[str, Any]:
    """Compute + persist the hash lock, stamping verification.hash on each item."""
    manifest = compute_manifest(items)
    for it in items:
        entry = manifest["items"].get(it.get("id"))
        if entry:
            it.setdefault("verification", {})["hash"] = entry["hash"]
    write_manifest(manifest, manifest_path)
    return manifest


def check_lock(
    items: list[dict[str, Any]], manifest: dict[str, Any]
) -> list[Issue]:
    """Detect edits made after a lock (hash mismatch) or missing/unknown items."""
    issues: list[Issue] = []
    locked = manifest.get("items", {})
    for it in items:
        iid = it.get("id")
        if iid not in locked:
            issues.append(
                Issue("error", "NOT_LOCKED", f"item {iid!r} not present in manifest", iid)
            )
            continue
        current = hash_item(it)
        if current != locked[iid]["hash"]:
            issues.append(
                Issue(
                    "error",
                    "HASH_MISMATCH",
                    f"item {iid!r} was edited after locking "
                    f"(locked {locked[iid]['hash'][:12]}..., now {current[:12]}...) "
                    f"— bump version + changelog",
                    iid,
                )
            )
    for iid in locked:
        if not any(it.get("id") == iid for it in items):
            issues.append(
                Issue("warning", "GONE_FROM_SET", f"locked item {iid!r} no longer in set", iid)
            )
    return issues
