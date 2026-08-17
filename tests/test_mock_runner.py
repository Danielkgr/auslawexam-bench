"""Tests for the deterministic offline mock runner."""

from __future__ import annotations

from auslex.config import ModelSpec
from auslex.runners import MockRunner, get_runner, is_mock_runner
from conftest import make_item


def _mock_spec(**over):
    base = dict(
        name="gpt",
        vendor="openai",
        model="gpt-5.6",
        runner="mock",
        mock_quality=0.86,
        mock_fabricate_rate=0.5,
    )
    base.update(over)
    return ModelSpec(**base)


def test_mock_is_flagged_and_ok():
    runner = MockRunner(_mock_spec())
    item = make_item()
    resp = runner.complete([], seed=0, item=item)
    assert resp.is_mock is True
    assert resp.ok is True
    assert resp.text
    assert resp.model.startswith("mock:")
    assert resp.cost_usd == 0.0


def test_mock_is_deterministic_for_same_seed():
    item = make_item()
    a = MockRunner(_mock_spec()).complete([], seed=42, item=item)
    b = MockRunner(_mock_spec()).complete([], seed=42, item=item)
    assert a.text == b.text
    assert a.finish_reason == b.finish_reason == "stop"


def test_mock_get_runner_factory():
    runner = get_runner(_mock_spec())
    assert is_mock_runner(runner) is True


def test_mock_degenerate_no_item():
    runner = MockRunner(_mock_spec())
    resp = runner.complete([], seed=0, item=None)
    assert resp.is_mock is True
    assert "(no item supplied)" in resp.text
