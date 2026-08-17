"""Tests for citation extraction + on_point / known_other / fabricated classification."""

from __future__ import annotations

from auslex.score.citations import (
    assess_answer,
    build_known_corpus,
    extract_citations,
)
from conftest import make_item


def test_extract_case_and_statute():
    text = (
        "The rule is in Smith v Jones (2020) 270 ALR 1 and the "
        "Civil Liability Act 2002 (Cth) s 5."
    )
    cites = extract_citations(text)
    kinds = {c.kind for c in cites}
    assert kinds == {"case", "statute"}
    assert any("Smith v Jones" in c.raw for c in cites)
    assert any("Civil Liability" in c.raw for c in cites)


def test_no_citations_in_plain_prose():
    assert extract_citations("This is a clean answer with no citations.") == []


def test_on_point_classification():
    item = make_item()
    corpus = build_known_corpus([item])
    text = "The rule is in Smith v Jones (2020) 270 ALR 1."
    rep = assess_answer(item, text, corpus)
    assert rep.total >= 1
    assert rep.on_point >= 1
    assert rep.fabricated == 0


def test_fabricated_classification():
    item = make_item()
    corpus = build_known_corpus([item])
    # An invented case that is in neither the item's authorities nor the corpus.
    text = "See also Meridian Holdings Pty Ltd v Copperfield Pty Ltd (2021) 150 ALR 22."
    rep = assess_answer(item, text, corpus)
    assert rep.total == 1
    assert rep.fabricated == 1
    assert rep.on_point == 0
    assert rep.fabricated_rate == 1.0


def test_known_other_classification():
    item_a = make_item()
    item_b = make_item(
        id="auslex-2026-0003",
        required_authorities=[
            {"kind": "case", "cite": "Brown v Green (2019) 265 ALR 9"},
        ],
    )
    corpus = build_known_corpus([item_a, item_b])
    # A real authority from item_b, cited inside an answer to item_a:
    # not on-point for item_a, but present in the whole-set corpus.
    rep = assess_answer(item_a, "Compare Brown v Green (2019) 265 ALR 9.", corpus)
    assert rep.total == 1
    assert rep.known_other == 1
    assert rep.on_point == 0
    assert rep.fabricated == 0


def test_fabricated_rate_is_zero_with_no_citations():
    rep = assess_answer(make_item(), "No citations here.", build_known_corpus([make_item()]))
    assert rep.total == 0
    assert rep.fabricated_rate == 0.0


def test_default_corpus_is_single_item():
    item = make_item()
    # Without passing a corpus, only this item's authorities are "known".
    rep = assess_answer(item, "See Smith v Jones (2020) 270 ALR 1.")
    assert rep.on_point >= 1
