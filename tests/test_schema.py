"""Tests for the pydantic item schema (valid/invalid items)."""

from __future__ import annotations

import pytest

from auslex.schema import validate_item
from conftest import make_item, make_mcq


def test_valid_item_passes():
    item = validate_item(make_item())
    assert item.id == "auslex-2026-0001"
    assert item.rubric_total == item.marks


def test_valid_mcq_passes():
    item = validate_item(make_mcq())
    assert item.type == "mcq"
    assert item.mcq_correct == 1


def test_bad_type_fails():
    with pytest.raises(ValueError):
        validate_item(make_item(type="multiple_choice"))


def test_bad_id_fails():
    with pytest.raises(ValueError):
        validate_item(make_item(id="not-a-valid-id"))


def test_bad_version_fails():
    with pytest.raises(ValueError):
        validate_item(make_item(version="1.0"))


def test_non_au_jurisdiction_fails():
    with pytest.raises(ValueError):
        validate_item(make_item(jurisdiction=["US"]))


def test_bad_priestley_area_fails():
    with pytest.raises(ValueError):
        validate_item(make_item(priestley_area="astrology"))


def test_rubric_sum_must_equal_marks():
    bad = make_item(
        rubric=[
            {"criterion": "rule", "max": 10},
            {"criterion": "application", "max": 5},  # sums to 15 != 20
        ]
    )
    with pytest.raises(ValueError):
        validate_item(bad)


def test_bad_canary_fails():
    with pytest.raises(ValueError):
        validate_item(make_item(canary="nope"))


def test_empty_question_text_fails():
    with pytest.raises(ValueError):
        validate_item(make_item(question_text="   "))


def test_mcq_requires_options_and_correct():
    bad = make_mcq(mcq_options=None, mcq_correct=None)
    with pytest.raises(ValueError):
        validate_item(bad)


def test_mcq_correct_out_of_range_fails():
    bad = make_mcq(mcq_options=["A", "B"], mcq_correct=5)
    with pytest.raises(ValueError):
        validate_item(bad)


def test_bad_date_fails():
    with pytest.raises(ValueError):
        validate_item(make_item(law_as_at="01/01/2026"))


def test_error_message_is_readable():
    # A failed validation should point at the offending item and field.
    with pytest.raises(ValueError) as exc:
        validate_item(make_item(id="bad-id", priestley_area="astrology"))
    msg = str(exc.value)
    assert "bad-id" in msg or "schema error" in msg
