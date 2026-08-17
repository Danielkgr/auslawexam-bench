"""Paired permutation test (pure Python, seeded).

The fair comparison between two models is on the *same* questions. For every
question both models answered, form the paired difference d_i = a_i - b_i.
The observed test statistic is T = mean(d). Under the null of no true
difference we randomise the *sign* of each paired difference (equivalently:
randomly swap which model is "a" on each question) and count how often the
resampled statistic reaches or exceeds the observed value in magnitude.

Because the question set is fixed and the seed is fixed, the p-value is fully
reproducible.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Mapping


@dataclass
class PermutationResult:
    a: str
    b: str
    n_pairs: int
    mean_diff: float          # mean(a - b) over shared questions
    p_value: float            # two-sided
    n_perm: int
    seed: int

    @property
    def significant(self, alpha: float = 0.05) -> bool:
        return self.p_value < alpha

    def to_dict(self) -> dict:
        return {
            "a": self.a,
            "b": self.b,
            "n_pairs": self.n_pairs,
            "mean_diff": round(self.mean_diff, 4),
            "p_value": round(self.p_value, 5),
            "n_perm": self.n_perm,
            "seed": self.seed,
            "significant_05": self.significant,
        }


def _paired_diffs(
    a: Mapping[str, float], b: Mapping[str, float]
) -> list[float]:
    common = [k for k in a if k in b]
    common.sort()  # deterministic ordering
    return [a[k] - b[k] for k in common]


def paired_permutation(
    a: Mapping[str, float],
    b: Mapping[str, float],
    *,
    a_name: str = "a",
    b_name: str = "b",
    n_perm: int = 10_000,
    seed: int = 0,
) -> PermutationResult:
    """Two-sided paired permutation test on question-level scores.

    ``a`` and ``b`` map question_id -> score. Only questions present in *both*
    are used (paired design).
    """
    diffs = _paired_diffs(a, b)
    n = len(diffs)
    if n < 2:
        raise ValueError("need at least 2 shared questions for a permutation test")

    t_obs = sum(diffs) / n
    rng = random.Random(seed)
    n_extreme = 0
    # Include the observed configuration in the null reference distribution.
    for _ in range(n_perm):
        perm = [d if rng.random() < 0.5 else -d for d in diffs]
        t_perm = sum(perm) / n
        if abs(t_perm) >= abs(t_obs):
            n_extreme += 1
    # Add 1 (observed) to both numerator and denominator for a conservative
    # finite-sample estimate; avoids p == 0.
    p_value = (n_extreme + 1) / (n_perm + 1)
    return PermutationResult(
        a=a_name, b=b_name, n_pairs=n, mean_diff=t_obs,
        p_value=p_value, n_perm=n_perm, seed=seed,
    )
