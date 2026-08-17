"""Tests for the paired permutation (sign-flip) test."""

from __future__ import annotations

import pytest

from auslex.stats.permutation import paired_permutation


def test_reproducible_for_fixed_seed():
    a = {"q1": 80.0, "q2": 75.0, "q3": 90.0, "q4": 85.0}
    b = {"q1": 70.0, "q2": 72.0, "q3": 80.0, "q4": 78.0}
    r1 = paired_permutation(a, b, n_perm=1000, seed=7)
    r2 = paired_permutation(a, b, n_perm=1000, seed=7)
    assert r1.p_value == r2.p_value
    assert r1.mean_diff == r2.mean_diff


def test_p_value_in_valid_range():
    a = {"q1": 80.0, "q2": 75.0, "q3": 90.0, "q4": 85.0}
    b = {"q1": 71.0, "q2": 73.0, "q3": 81.0, "q4": 79.0}
    r = paired_permutation(a, b, n_perm=2000, seed=0)
    lo = 1 / (r.n_perm + 1)
    assert lo <= r.p_value <= 1.0


def test_needs_at_least_two_shared_questions():
    with pytest.raises(ValueError):
        paired_permutation({"q1": 80.0}, {"q1": 70.0}, n_perm=100)


def test_only_shared_questions_are_used():
    a = {"q1": 80.0, "q2": 75.0, "q3": 90.0}
    b = {"q2": 72.0, "q3": 80.0, "q4": 99.0}
    r = paired_permutation(a, b, n_perm=500, seed=1)
    # Shared question ids are {q2, q3}.
    assert r.n_pairs == 2


def test_identical_scores_gives_p_one():
    s = {"q1": 80.0, "q2": 75.0, "q3": 90.0, "q4": 85.0}
    r = paired_permutation(dict(s), dict(s), n_perm=1000, seed=3)
    assert r.mean_diff == 0.0
    assert r.p_value == 1.0


def test_superior_model_gives_smaller_p_than_noise():
    # A strongly, consistently better model A should beat a random split.
    a = {f"q{i}": 90.0 for i in range(6)}
    b = {f"q{i}": 70.0 for i in range(6)}
    c = {f"q{i}": (90.0 if i % 2 else 70.0) for i in range(6)}
    strong = paired_permutation(a, b, n_perm=2000, seed=5).p_value
    split = paired_permutation(c, dict(b), n_perm=2000, seed=5).p_value
    assert strong < split
    assert strong < 0.05
