"""Tests for IO + content hashing."""

from __future__ import annotations

from auslex.io import (
    canonical_json,
    hash_item,
    read_jsonl,
    write_jsonl,
)
from conftest import make_item


def test_canonical_json_key_order_independent():
    assert canonical_json({"a": 1, "b": 2}) == canonical_json({"b": 2, "a": 1})


def test_hash_item_is_stable():
    item = make_item()
    assert hash_item(item) == hash_item(item)


def test_hash_changes_on_content_edit():
    a = make_item()
    b = make_item(gold_answer="A completely different gold answer.")
    assert hash_item(a) != hash_item(b)


def test_hash_ignores_verification_hash():
    # Only the volatile verification.hash (the self-content-hash written at
    # lock time) is excluded from the content hash.
    a = make_item(verification={})
    b = make_item(verification={"hash": "deadbeef"})
    assert hash_item(a) == hash_item(b)


def test_hash_includes_other_verification_fields():
    # Legit verification content (who/when verified) is part of the item.
    a = make_item(verification={})
    b = make_item(verification={"verifier": "lawyer-x"})
    assert hash_item(a) != hash_item(b)


def test_hash_differs_on_other_field():
    a = make_item(marks=20)
    b = make_item(marks=25)
    assert hash_item(a) != hash_item(b)


def test_jsonl_roundtrip(tmp_path):
    path = tmp_path / "out" / "items.jsonl"
    rows = [make_item(), make_item(id="auslex-2026-0002")]
    write_jsonl(path, rows)
    assert path.exists()
    back = read_jsonl(path)
    assert len(back) == 2
    assert back[0]["id"] == "auslex-2026-0001"
    assert back[1]["id"] == "auslex-2026-0002"
