"""Human calibration + inter-rater agreement (Cohen's kappa).

The automated judge is validated against human graders: a human assigns each
answer a mark band, we compare the human band to the judge's band, and report
Cohen's kappa (chance-adjusted agreement). Kappa is computed in pure Python for
reproducibility.
"""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass
from typing import Sequence

# Mark bands (percentage of marks available) — the coarse buckets human and
# judge are compared on, which keeps the kappa well-defined and gradable.
BANDS = [
    ("fail", 0.0, 0.50),
    ("pass", 0.50, 0.65),
    ("credit", 0.65, 0.75),
    ("distinction", 0.75, 0.85),
    ("high_distinction", 0.85, 1.01),
]


def band(score_100: float) -> str:
    s = score_100 / 100.0
    for name, lo, hi in BANDS:
        if lo <= s < hi:
            return name
    return BANDS[-1][0]


def cohen_kappa(a: Sequence[str], b: Sequence[str]) -> float:
    """Chance-adjusted agreement between two categorical label sequences."""
    if len(a) != len(b):
        raise ValueError("label sequences must be equal length")
    n = len(a)
    if n == 0:
        return float("nan")
    po = sum(1 for x, y in zip(a, b) if x == y) / n
    ca, cb = Counter(a), Counter(b)
    cats = set(ca) | set(cb)
    pe = sum((ca[c] / n) * (cb[c] / n) for c in cats)
    if math.isclose(pe, 1.0):
        return 1.0 if po == 1.0 else 0.0
    return (po - pe) / (1.0 - pe)


@dataclass
class Agreement:
    n: int
    observed: float
    expected: float
    kappa: float

    def to_dict(self) -> dict:
        return {
            "n": self.n,
            "observed_agreement": round(self.observed, 4),
            "expected_agreement": round(self.expected, 4),
            "cohen_kappa": round(self.kappa, 4),
        }


def kappa_between_bands(
    human_bands: Sequence[str], judge_bands: Sequence[str]
) -> Agreement:
    n = len(human_bands)
    if len(human_bands) != len(judge_bands) or n == 0:
        raise ValueError("band sequences must be equal, non-empty length")
    po = sum(1 for x, y in zip(human_bands, judge_bands) if x == y) / n
    ca, cb = Counter(human_bands), Counter(judge_bands)
    cats = set(ca) | set(cb)
    pe = sum((ca[c] / n) * (cb[c] / n) for c in cats)
    kappa = (po - pe) / (1.0 - pe) if not math.isclose(pe, 1.0) else (1.0 if po == 1.0 else 0.0)
    return Agreement(n=n, observed=po, expected=pe, kappa=kappa)
