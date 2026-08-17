"""Deterministic offline mock runner.

Used for the commercial model slots when no API key is configured (and as a
safety fallback if a local endpoint is unreachable). It synthesises a plausible
exam-style answer from the *item* — citing a quality-dependent subset of the
item's ``required_authorities`` and, with a controllable rate, inserting a
fabricated citation — so the downstream citation checker, judge, and statistics
all operate on realistic, reproducible input.

Everything is seeded from ``(slot, item_id, rep)`` and is therefore exactly
reproducible. Mock outputs are flagged ``is_mock=True`` end-to-end and are
labelled as synthetic on the leaderboard — they are never presented as real
model outputs.
"""

from __future__ import annotations

import hashlib
import random
from typing import Optional

from ..config import ModelSpec
from .base import Runner, RawResponse

_FAKE_PARTIES = [
    "Meridian", "Harbourlight", "Copperfield", "Redgum", "Saltwater",
    "Ironbark", "Wattle", "Cairn", "Boulder", "Tarn", "Gulaga", "Orara",
]
_FAKE_RPT = ["ALR", "ALJR", "NSWR", "VLR", "SASR", "CrL R"]
_FAKE_YEAR = [2019, 2021, 2022, 2023, 2024, 2025]


def _seeded_rng(slot: str, item_id: str, seed: Optional[int]) -> random.Random:
    key = f"{slot}|{item_id}|{seed if seed is not None else 0}"
    h = int(hashlib.sha256(key.encode("utf-8")).hexdigest(), 16)
    return random.Random(h)


def _fabricate_case(rng: random.Random) -> str:
    a = rng.choice(_FAKE_PARTIES)
    b = rng.choice(_FAKE_PARTIES)
    while b == a:
        b = rng.choice(_FAKE_PARTIES)
    yr = rng.choice(_FAKE_YEAR)
    vol = rng.randint(100, 260)
    rep = rng.choice(_FAKE_RPT)
    pg = rng.randint(1, 420)
    return f"{a} Holdings Pty Ltd v {b} Pty Ltd ({yr}) {vol} {rep} {pg}"


def _build_answer(item: dict, quality: float, fabricate_rate: float, rng: random.Random) -> str:
    topics = item.get("topics", [])
    juris = ", ".join(item.get("jurisdiction", [])) or "Australian"
    authors = item.get("required_authorities", [])
    key_issues = item.get("key_issues", [])

    parts: list[str] = []
    t = " and ".join(topics[:2]) or "the relevant area of law"
    parts.append(f"The question raises issues concerning {t} under {juris} law.")

    # Rule statements: a quality-dependent subset of the required authorities.
    if authors:
        n_cite = max(1, round(len(authors) * quality))
        for a in authors[:n_cite]:
            parts.append(f"The governing rule is found in {a.get('cite')}.")
    else:
        parts.append("The governing rule is found in the relevant statute.")

    if quality < 0.6:
        parts.append("The provision sets out the elements that must be established on the facts.")

    if key_issues:
        n_issues = max(1, round(len(key_issues) * quality))
        parts.append(
            "The core issues to be addressed include: " + "; ".join(key_issues[:n_issues]) + "."
        )

    parts.append(
        "On these facts, applying the rule, the outcome turns on those elements as applied to the pleaded facts."
    )

    if quality >= 0.7:
        parts.append(
            "The opposing party may contend that the rule does not apply; that contention is best answered by reference to the authority above."
        )

    # Controllable fabrication: an invented case citation.
    if authors and rng.random() < fabricate_rate:
        parts.append(f"See also {_fabricate_case(rng)} for a contrary position.")

    parts.append(
        "In conclusion, the better view favours the position analysed above, subject to the caveats identified."
    )
    return "\n\n".join(parts)


class MockRunner(Runner):
    def complete(
        self,
        messages: list[dict[str, str]],
        *,
        seed: Optional[int] = None,
        item: Optional[dict] = None,
    ) -> RawResponse:
        if item is None:
            # Degenerate: produce a short deterministic stub.
            text = f"[mock {self.spec.name}] (no item supplied)"
            return RawResponse(text=text, is_mock=True, model=self.spec.model, cost_usd=0.0)

        rng = _seeded_rng(self.spec.name, item.get("id", "?"), seed)
        text = _build_answer(
            item,
            quality=self.spec.mock_quality,
            fabricate_rate=self.spec.mock_fabricate_rate,
            rng=rng,
        )
        # Deterministic-ish token estimate from text length.
        completion_tokens = max(1, len(text) // 4)
        return RawResponse(
            text=text,
            reasoning=None,
            finish_reason="stop",
            prompt_tokens=0,
            completion_tokens=completion_tokens,
            latency_ms=int(rng.randint(400, 1800)),
            cost_usd=0.0,
            system_fingerprint=f"mock-{self.spec.name}",
            model=f"mock:{self.spec.model}",
            is_mock=True,
        )
