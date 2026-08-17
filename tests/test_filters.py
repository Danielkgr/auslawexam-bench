"""Tests for the hard jurisdiction rule (gold answers must be AU-only)."""

from __future__ import annotations

from auslex.ingest.filters import (
    check_item,
    find_non_au,
    lint_gold_answer,
    lint_question,
)
from conftest import make_item


def test_clean_gold_answer_has_no_issues():
    issues = lint_gold_answer(
        "The rule is in Smith v Jones (2020) 270 ALR 1 and the "
        "Civil Liability Act 2002 (Cth) s 5."
    )
    assert issues == []


def test_us_reporter_is_a_hard_error():
    issues = lint_gold_answer("Compare Roe v Wade, 410 U.S. 113 (1973).")
    assert any(i.code == "GOLD_NON_AU" and i.level == "error" for i in issues)


def test_ukhl_reporter_is_flagged():
    hits = find_non_au("DPP v Bow St, [1991] 2 UKHL 12.")
    assert any("UKHL" in h["match"] or "UKHL" in h["pattern"] for h in hits)


def test_english_law_phrase_is_flagged():
    assert find_non_au("This follows English law as applied by English courts.") != []


def test_house_of_lords_phrase_is_flagged():
    assert find_non_au("The House of Lords held otherwise.") != []


def test_us_supreme_court_phrase_is_flagged():
    assert find_non_au("The US Supreme Court has held otherwise.") != []


def test_gold_non_au_is_error_and_question_is_warning():
    assert all(i.level == "error" for i in lint_gold_answer("410 U.S. 113"))
    assert all(i.level == "warning" for i in lint_question("cf. 410 U.S. 113"))


def test_check_item_flags_non_au_authority():
    item = make_item(
        required_authorities=[{"kind": "case", "cite": "Roe v Wade, 410 U.S. 113 (1973)"}]
    )
    issues = check_item(item)
    assert any(i.code == "AUTH_NON_AU" for i in issues)


def test_check_item_clean_item_has_no_issues():
    assert check_item(make_item()) == []


def test_au_reporters_are_not_false_positives():
    # Legitimate Australian citations must not trip the lint.
    text = (
        "Mabo v Queensland (No 2) (1992) 175 CLR 1; see also "
        "Waltons Stores (Interstate) Ltd v Maher (1988) 164 CLR 387 "
        "and the Corporations Act 2001 (Cth) s 135."
    )
    assert find_non_au(text) == []
