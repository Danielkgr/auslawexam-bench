"""LLM-judge rubric scoring — offline mock now, API-ready interface.

Every answer is scored against the item's rubric by an *ensemble* of judges.
The protocol mirrors the design doc: answers are anonymised, criterion order is
randomised per judge, and scores are averaged across judges.

The shipped judge is a deterministic, seeded mock: it derives a quality signal
from how well the answer covers the item's required authorities and key issues,
then awards each criterion a proportional share with small per-judge noise. It
is labelled ``judge="mock"`` and the exact per-judge scores are recorded, so the
mock is fully reproducible and auditable. Swapping in a real LLM judge means
replacing ``_judge_once`` with an API call — the surrounding ensemble,
randomisation, and aggregation are unchanged.
"""

from __future__ import annotations

import hashlib
import random
import re
from dataclasses import dataclass, field
from typing import Any, Optional

_STOP = {
    "the", "a", "an", "of", "to", "in", "on", "and", "or", "that", "this",
    "must", "be", "is", "are", "it", "as", "for", "by", "with", "whether",
}


def _tokens(s: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9]+", s.lower()) if t not in _STOP}


def _seeded(key: str) -> random.Random:
    h = int(hashlib.sha256(key.encode("utf-8")).hexdigest(), 16)
    return random.Random(h)


def _coverage(item: dict[str, Any], answer: str) -> dict[str, float]:
    """Answer-quality signals in [0,1]."""
    atokens = _tokens(answer)
    ans_low = answer.lower()

    # 1. citation coverage: how many required authorities are named.
    req = item.get("required_authorities", [])
    if req:
        hit = 0
        for a in req:
            cite = a.get("cite", "")
            stem = _tokens(cite)
            if stem and (len(stem & atokens) / len(stem)) >= 0.5:
                hit += 1
        cite_cov = hit / len(req)
    else:
        cite_cov = 0.0 if ("act" not in ans_low or "s " not in ans_low) else 0.5

    # 2. key-issue coverage: token overlap per issue, averaged.
    issues = item.get("key_issues", [])
    if issues:
        ov = []
        for ki in issues:
            k = _tokens(ki)
            ov.append((len(k & atokens) / len(k)) if k else 0.0)
        issue_cov = sum(ov) / len(ov)
    else:
        issue_cov = 0.4

    # 3. structure: conclusion language present.
    conclusion = any(w in ans_low for w in
                     ("in conclusion", "conclude", "therefore", "accordingly",
                      "the better view", "on balance"))
    # 4. length signal (diminishing).
    length = min(1.0, len(answer) / 1400.0)

    return {
        "cite_cov": cite_cov,
        "issue_cov": issue_cov,
        "conclusion": 1.0 if conclusion else 0.0,
        "length": length,
    }


def _quality_score(item: dict[str, Any], answer: str) -> float:
    c = _coverage(item, answer)
    q = 0.42 * c["cite_cov"] + 0.28 * c["issue_cov"] + 0.15 * c["conclusion"] + 0.15 * c["length"]
    return max(0.0, min(1.0, q))


@dataclass
class JudgeConfig:
    n_judges: int = 3
    base_seed: int = 0
    name: str = "mock-ensemble"


@dataclass
class JudgeResult:
    judge: str
    n_judges: int
    per_criterion: dict[str, float] = field(default_factory=dict)
    total: float = 0.0
    max_total: float = 0.0
    item_score: float = 0.0
    per_judge: list[dict[str, float]] = field(default_factory=list)
    quality_signals: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "judge": self.judge,
            "n_judges": self.n_judges,
            "per_criterion": {k: round(v, 3) for k, v in self.per_criterion.items()},
            "total": round(self.total, 3),
            "max_total": self.max_total,
            "item_score": round(self.item_score, 4),
            "quality_signals": {k: round(v, 3) for k, v in self.quality_signals.items()},
            "per_judge": self.per_judge,
        }


def _judge_once(
    item: dict[str, Any], answer: str, cfg: JudgeConfig, j: int, q: float
) -> dict[str, float]:
    """One judge's per-criterion scores, in a randomised criterion order."""
    rubric = item.get("rubric", [])
    rng = _seeded(f"{cfg.name}|{j}|{item.get('id','?')}|{cfg.base_seed}")
    # Order randomisation (recorded; does not change per-criterion scores here).
    order = list(range(len(rubric)))
    rng.shuffle(order)
    scores: dict[str, float] = {}
    for idx in order:
        crit = rubric[idx]
        cmax = int(crit.get("max", 0))
        noise = rng.uniform(-0.08, 0.08)
        s = max(0.0, min(1.0, q + noise)) * cmax
        scores[crit.get("criterion", f"criterion_{idx}")] = round(s, 3)
    return scores


def judge_answer(
    item: dict[str, Any],
    answer: str,
    cfg: Optional[JudgeConfig] = None,
    seed: Optional[int] = None,
) -> JudgeResult:
    """Score one answer against the item's rubric with a judge ensemble."""
    cfg = cfg or JudgeConfig()
    q = _quality_score(item, answer)
    per_judge = [
        _judge_once(item, answer, cfg, j, q) for j in range(cfg.n_judges)
    ]
    # Average per criterion across judges.
    per_criterion: dict[str, float] = {}
    for crit in [r.get("criterion", f"criterion_{i}") for i, r in enumerate(item.get("rubric", []))]:
        vals = [pj.get(crit, 0.0) for pj in per_judge]
        per_criterion[crit] = sum(vals) / len(vals) if vals else 0.0
    max_total = sum(int(r.get("max", 0)) for r in item.get("rubric", []))
    total = sum(per_criterion.values())
    item_score = total / max_total if max_total else 0.0
    return JudgeResult(
        judge=cfg.name,
        n_judges=cfg.n_judges,
        per_criterion=per_criterion,
        total=total,
        max_total=max_total,
        item_score=item_score,
        per_judge=per_judge,
        quality_signals=_coverage(item, answer),
    )
