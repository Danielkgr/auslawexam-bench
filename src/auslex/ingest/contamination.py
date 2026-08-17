"""Contamination controls: n-gram overlap + in-dataset dedup.

Two checks:

* **Corpus overlap** — flag candidate questions that overlap a known public exam
  corpus (Tier-A anchors) beyond a threshold. We do *not* ship Tier-B university
  papers, so the corpus is whatever the operator points us at (e.g. a local
  folder of Tier-A past papers they are licensed to reference). With no corpus
  supplied this check is a documented no-op.
* **In-dataset dedup** — flag pairs of items in the candidate set that are
  suspiciously similar to each other (accidental authoring duplication).

The n-gram metric is language-agnostic and cheap; it is a tripwire, not a
verdict — anything flagged is sent back to a human, not auto-rejected.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Iterable, Optional

from .issues import Issue

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall((text or "").lower())


def ngrams(tokens: list[str], n: int) -> set[tuple[str, ...]]:
    if len(tokens) < n:
        return {tuple(tokens)} if tokens else set()
    return {tuple(tokens[i : i + n]) for i in range(len(tokens) - n + 1)}


@dataclass
class Overlap:
    a: str
    b: str
    fraction: float  # fraction of a's n-grams present in b
    shared: int
    total: int


def max_overlap(a: str, b: str, n: int = 8) -> Overlap:
    """Fraction of ``a``'s n-grams that also appear in ``b`` (directional)."""
    ga, gb = ngrams(tokenize(a), n), ngrams(tokenize(b), n)
    if not ga:
        return Overlap(a, b, 0.0, 0, 0)
    shared = len(ga & gb)
    return Overlap(a, b, shared / len(ga), shared, len(ga))


def check_against_corpus(
    text: str,
    corpus_texts: Iterable[str],
    n: int = 8,
    threshold: float = 0.30,
    item_id: Optional[str] = None,
) -> list[Issue]:
    """Flag ``text`` if it overlaps any corpus document beyond ``threshold``."""
    issues: list[Issue] = []
    for doc in corpus_texts:
        ov = max_overlap(text, doc, n=n)
        if ov.fraction >= threshold and ov.total > 0:
            issues.append(
                Issue(
                    level="warning",
                    code="CORPUS_OVERLAP",
                    message=(
                        f"question overlaps a known corpus document by "
                        f"{ov.fraction:.0%} of its {n}-grams "
                        f"({ov.shared}/{ov.total}) — possible training-data leak"
                    ),
                    item_id=item_id,
                )
            )
    return issues


def dedup_items(
    items: list[dict[str, Any]],
    n: int = 8,
    threshold: float = 0.30,
) -> list[Issue]:
    """Flag in-dataset pairs of items whose question stems are too similar."""
    issues: list[Issue] = []
    texts = [(it.get("id"), it.get("question_text", "")) for it in items]
    for i in range(len(texts)):
        for j in range(i + 1, len(texts)):
            a_id, a_text = texts[i]
            b_id, b_text = texts[j]
            ov = max_overlap(a_text, b_text, n=n)
            if ov.fraction >= threshold and ov.total > 0:
                issues.append(
                    Issue(
                        level="warning",
                        code="DEDUP",
                        message=(
                            f"{a_id} and {b_id} share {ov.fraction:.0%} of "
                            f"{n}-grams ({ov.shared}/{ov.total}) — near-duplicate?"
                        ),
                        item_id=a_id,
                    )
                )
    return issues
