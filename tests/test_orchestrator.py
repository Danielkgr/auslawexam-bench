"""Concurrency, retry, and ordering in the run orchestrator."""

from __future__ import annotations

import threading

from conftest import sample_items

from auslex.config import ModelSpec
from auslex.run.orchestrator import RunConfig, complete_with_retry, is_transient, run
from auslex.run.storage import RunStore
from auslex.runners import RawResponse


def _mock(name: str) -> ModelSpec:
    return ModelSpec(name=name, vendor="local", model=name, runner="mock")


def _records(tmp_path, concurrency: int) -> list[dict]:
    cfg = RunConfig(
        models=[_mock("a"), _mock("b")],
        items=sample_items(),
        n_reps=3,
        run_id=f"c{concurrency}",
        out_root=tmp_path,
        concurrency=concurrency,
    )
    run(cfg)
    return RunStore(tmp_path, f"c{concurrency}").records()


def test_records_are_identical_whatever_the_concurrency(tmp_path):
    def key(r):
        return (r["model"], r["item_id"], r["rep"], r["text"], r["prompt_hash"])

    serial = [key(r) for r in _records(tmp_path, 1)]
    parallel = [key(r) for r in _records(tmp_path, 8)]
    assert serial == parallel
    # Model, then item, then repetition.
    assert [k[:3] for k in serial] == sorted(k[:3] for k in serial)


def test_transient_errors_are_retried_with_backoff():
    calls, sleeps = [], []
    replies = [
        RawResponse(text="", error="HTTP 429 from x: slow down"),
        RawResponse(text="", error="HTTP 503 from x: busy"),
        RawResponse(text="an answer"),
    ]

    def call():
        calls.append(1)
        return replies[len(calls) - 1]

    resp, attempts = complete_with_retry(call, max_retries=2, base_delay=1.0, sleep=sleeps.append)
    assert resp.ok and attempts == 3 and sleeps == [1.0, 2.0]


def test_permanent_errors_are_not_retried():
    resp, attempts = complete_with_retry(
        lambda: RawResponse(text="", error="HTTP 400 from x: bad request"),
        max_retries=3,
        base_delay=0,
        sleep=lambda s: None,
    )
    assert attempts == 1 and not resp.ok
    assert not is_transient("refusal: the model declined to answer")
    assert is_transient("connection error: reset") and is_transient("rate limited (HTTP 429): x")


def test_calls_really_run_concurrently(tmp_path, monkeypatch):
    from auslex.runners.mock_runner import MockRunner

    active, peak = [0], [0]
    lock = threading.Lock()
    original = MockRunner.complete

    def slow(self, *args, **kwargs):
        with lock:
            active[0] += 1
            peak[0] = max(peak[0], active[0])
        threading.Event().wait(0.02)
        with lock:
            active[0] -= 1
        return original(self, *args, **kwargs)

    monkeypatch.setattr(MockRunner, "complete", slow)
    run(
        RunConfig(
            models=[_mock("a")],
            items=sample_items(),
            n_reps=4,
            run_id="p",
            out_root=tmp_path,
            concurrency=4,
        )
    )
    assert peak[0] > 1
