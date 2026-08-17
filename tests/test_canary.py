"""Tests for BIG-bench style canary generation + leak detection."""

from __future__ import annotations

import re

from auslex.canary import (
    GLOBAL_CANARY,
    _CANARY_RE,
    find_canaries,
    has_canary,
    make_canary,
    random_canary,
)


def test_make_canary_is_deterministic():
    assert make_canary("auslex-2026-0001") == make_canary("auslex-2026-0001")


def test_make_canary_differs_by_id():
    assert make_canary("auslex-2026-0001") != make_canary("auslex-2026-0002")


def test_make_canary_shape():
    c = make_canary("auslex-2026-0001")
    assert c.startswith("auslex:")
    assert re.match(r"^auslex:[0-9a-f]{12}$", c) is not None
    # A per-item canary must be detectable by the leak-detection regex.
    assert _CANARY_RE.search(c) is not None


def test_global_canary_is_detectable():
    text = f"here is a marker {GLOBAL_CANARY} embedded in prose"
    assert has_canary(text) is True
    assert GLOBAL_CANARY in find_canaries(text)


def test_no_canary_in_clean_text():
    assert has_canary("a perfectly clean legal answer") is False
    assert find_canaries("nothing to see here") == []
    assert find_canaries("") == []


def test_random_canary_matches_regex():
    c = random_canary()
    assert c.startswith("auslex:")
    assert _CANARY_RE.fullmatch(c) is not None
