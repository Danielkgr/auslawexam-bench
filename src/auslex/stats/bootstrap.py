"""Seeded bootstrap confidence intervals (pure Python, no numpy).

The design doc requires reproducible question-level resampling: a model's
headline numbers (mean item score, fabricated-citation rate) are quoted with a
bootstrap 95% CI obtained by resampling *questions* with replacement. Every
draw is driven by a fixed seed so a given input always yields the same
interval.
"""

from __future__ import annotations

import random
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any


@dataclass
class Interval:
    low: float
    high: float
    point: float
    n: int
    n_boot: int
    ci: float
    seed: int

    def to_dict(self) -> dict:
        return {
            "point": round(self.point, 4),
            "low": round(self.low, 4),
            "high": round(self.high, 4),
            "n": self.n,
            "n_boot": self.n_boot,
            "ci": self.ci,
            "seed": self.seed,
        }


def _percentile(xs: Sequence[float], q: float) -> float:
    """Linear-interpolated percentile (the standard type-7 / numpy default)."""
    if not xs:
        raise ValueError("cannot take percentile of an empty sample")
    xs = sorted(xs)
    if len(xs) == 1:
        return xs[0]
    rank = q * (len(xs) - 1)
    lo = int(rank)
    hi = min(lo + 1, len(xs) - 1)
    frac = rank - lo
    return xs[lo] + (xs[hi] - xs[lo]) * frac


def _mean(xs: Sequence[Any]) -> float:
    return sum(xs) / len(xs)


def bootstrap_ci(
    values: Sequence[Any],
    *,
    n_boot: int = 10_000,
    ci: float = 0.95,
    seed: int = 0,
    statistic: Callable[[Sequence[Any]], float] = _mean,
) -> Interval:
    """Bootstrap a statistic over ``values`` (one unit per question).

    Resamples the units (questions) with replacement and recomputes the same
    statistic on each draw, so the point estimate and the interval always
    describe the same quantity.  A unit can be a number or, for a pooled ratio,
    a (numerator, denominator) pair.
    """
    vals = list(values)
    n = len(vals)
    if n == 0:
        raise ValueError("need at least one question-level value")
    point = statistic(vals)

    rng = random.Random(seed)
    stats = [point]  # include the point estimate as a draw
    idx_range = range(n)
    for _ in range(n_boot):
        sample = [vals[i] for i in (rng.randrange(n) for _ in idx_range)]
        stats.append(statistic(sample))

    alpha = (1.0 - ci) / 2.0
    low = _percentile(stats, alpha)
    high = _percentile(stats, 1.0 - alpha)
    return Interval(low=low, high=high, point=point, n=n, n_boot=n_boot, ci=ci, seed=seed)
