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


# --- regression: the corpus must recognise its own authorities ------------- #

from auslex.cli import ROOT  # noqa: E402
from auslex.io import read_jsonl  # noqa: E402
from auslex.score.citations import _SEED_AUTHORITIES  # noqa: E402

_ITEMS = read_jsonl(ROOT / "data" / "questions" / "auslex.jsonl")
_CORPUS = build_known_corpus(_ITEMS)


def test_every_seed_authority_echoed_is_known_not_fabricated():
    """A model that cites a seed authority verbatim is citing a real case.

    Regression: the seed list used to enter the corpus un-normalised, so
    "Craig v South Australia (1995) 184 CLR 163" was classed as fabricated.
    """
    for cite in _SEED_AUTHORITIES:
        for item in _ITEMS:
            rep = assess_answer(item, f"The rule is stated in {cite}.", _CORPUS)
            assert rep.total >= 1, f"not extracted: {cite}"
            assert rep.fabricated == 0, f"{cite} classed as fabricated for {item['id']}"


def test_every_gold_authority_echoed_is_on_point_for_its_item():
    for item in _ITEMS:
        for auth in item["required_authorities"]:
            rep = assess_answer(item, f"See {auth['cite']}.", _CORPUS)
            assert rep.total >= 1, f"not extracted: {auth['cite']}"
            assert rep.on_point == rep.total, f"{auth['cite']} not on point for {item['id']}"


def test_matching_respects_token_boundaries():
    item = make_item(
        required_authorities=[
            {"kind": "statute", "cite": "Corporations Act 2001 (Cth) s 181"},
            {"kind": "case", "cite": "Waltons Stores (Interstate) Ltd v Maher (1988) 164 CLR 387"},
        ]
    )
    corpus = build_known_corpus([item])
    # s 18 is a different provision from s 181, and page 38 is not page 387.
    rep = assess_answer(item, "See the Corporations Act 2001 (Cth) s 18.", corpus)
    assert rep.fabricated == 1
    rep = assess_answer(item, "See (1988) 164 CLR 38.", corpus)
    assert rep.fabricated == 1
    # A subsection of the required section is still the required section.
    rep = assess_answer(item, "See the Corporations Act 2001 (Cth) s 181(1).", corpus)
    assert rep.on_point == 1


def test_lettered_sections_and_rules_are_extracted():
    text = (
        "A caveat takes effect under the Real Property Act 1900 (NSW) s 74H, and a pleading "
        "may be struck out under the Uniform Civil Procedure Rules 2005 (NSW) r 14.28."
    )
    raws = [c.raw for c in extract_citations(text)]
    assert any(r.endswith("s 74H") for r in raws), raws
    assert any(r.endswith("r 14.28") for r in raws), raws
