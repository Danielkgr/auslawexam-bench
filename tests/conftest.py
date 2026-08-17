"""Shared test fixtures and helpers for the auslex test suite."""

from __future__ import annotations

import sys
from pathlib import Path

# Make the tests directory importable (tests has no __init__.py).
sys.path.insert(0, str(Path(__file__).resolve().parent))


def make_item(**over):
    """A valid, schema-complete item dict. Override any field via ``**over``."""
    base = {
        "id": "auslex-2026-0001",
        "version": "0.1.0",
        "type": "short_answer",
        "jurisdiction": ["Cth"],
        "priestley_area": "contract",
        "topics": ["unjust enrichment", "mistake of fact"],
        "difficulty": "credit",
        "marks": 20,
        "question_text": "Explain the test for restitution for mistake of fact.",
        "gold_answer": (
            "The leading authority is Smith v Jones (2020) 270 ALR 1. See also "
            "the Civil Liability Act 2002 (Cth) s 5."
        ),
        "key_issues": ["mistake of fact", "unconscionability"],
        "required_authorities": [
            {"kind": "case", "cite": "Smith v Jones (2020) 270 ALR 1"},
            {"kind": "statute", "cite": "Civil Liability Act 2002 (Cth) s 5"},
        ],
        "rubric": [
            {"criterion": "rule", "max": 10},
            {"criterion": "application", "max": 10},
        ],
        "law_as_at": "2026-01-01",
        "provenance": {"tier": "C", "author": "test-author", "provisional": True},
        "verification": {},
        "canary": "auslex:0123456789ab",
    }
    base.update(over)
    return base


def make_mcq(**over):
    item = make_item(
        id="auslex-2026-0002",
        type="mcq",
        mcq_options=["A", "B", "C", "D"],
        mcq_correct=1,
    )
    item.update(over)
    return item


def sample_items():
    """Two valid items (one short answer, one MCQ) for end-to-end runs."""
    return [
        make_item(),
        make_mcq(),
    ]
