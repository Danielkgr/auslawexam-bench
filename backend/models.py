"""Pydantic models for the AusLawExam-Bench Evaluator API."""

from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


# --------------------------------------------------------------------------- #
# Credentials & slots
# --------------------------------------------------------------------------- #


class ApiKeyConfig(BaseModel):
    openai_key: Optional[str] = None
    anthropic_key: Optional[str] = None
    google_key: Optional[str] = None
    # Local slot fields.
    local_base_url: str = "http://localhost:10000/v1"
    local_model: str = "14. Qwen3.8-27B (Q5_K_M)"
    local_enable_thinking: bool = False


class SlotStatus(BaseModel):
    name: str
    vendor: str
    model: str
    is_real: bool
    is_mock: bool
    is_reachable: Optional[bool] = None
    key_present: bool
    base_url: Optional[str] = None


class TestConnectionResult(BaseModel):
    ok: bool
    detail: str = ""
    model_id: Optional[str] = None


# --------------------------------------------------------------------------- #
# Run configuration
# --------------------------------------------------------------------------- #


class RunConfig(BaseModel):
    models: list[str] = Field(default_factory=lambda: ["gpt", "claude", "gemini", "local"])
    n_reps: int = Field(default=3, ge=1, le=20)
    base_seed: int = Field(default=0, ge=0)
    run_id: Optional[str] = None  # optional explicit run id (auto-generated if omitted)
    question_filter: Optional[str] = None  # comma-separated question IDs
    priestley_filter: Optional[str] = None  # comma-separated area names
    jurisdiction_filter: Optional[str] = None  # comma-separated jurisdictions
    difficulty_filter: Optional[str] = None  # comma-separated difficulty levels


# --------------------------------------------------------------------------- #
# Run status
# --------------------------------------------------------------------------- #


class ModelProgress(BaseModel):
    name: str
    is_mock: bool
    n_done: int
    n_total: int
    n_ok: int
    n_error: int
    status: Literal["pending", "running", "done", "error"] = "pending"


class RunStatus(BaseModel):
    run_id: str
    status: Literal["running", "done", "error"]
    n_completions: int
    n_total: int
    n_ok: int
    n_error: int
    models: list[ModelProgress]
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    error_msg: Optional[str] = None


# --------------------------------------------------------------------------- #
# Results
# --------------------------------------------------------------------------- #


class CitationAudit(BaseModel):
    kind: str  # "case" | "statute"
    raw: str
    classification: Literal["on_point", "known_other", "fabricated"]


class ItemResult(BaseModel):
    run_id: str
    model: str
    item_id: str
    rep: int
    is_mock: bool
    priestley_area: str
    difficulty: str
    item_score_100: float
    fabricated_rate: float
    on_point_rate: float
    total_citations: int
    citations: list[CitationAudit]
    rubric: dict[str, float]
    answer_text: Optional[str] = None
    contamination_flag: bool = False


class LeaderboardModel(BaseModel):
    model: str
    is_mock: bool
    n_questions: int
    mean_item_score_100: dict[str, Any]
    fabricated_rate: dict[str, Any]
    per_difficulty: dict[str, Any]
    per_priestley: dict[str, Any]


class PairwiseResult(BaseModel):
    a: str
    b: str
    n_pairs: int
    mean_diff: float
    p_value: float
    significant_05: bool


class StatsReport(BaseModel):
    run_id: str
    n_questions_total: int
    n_models: int
    models: list[LeaderboardModel]
    pairwise_permutation: list[PairwiseResult]
    method: dict[str, Any]


# --------------------------------------------------------------------------- #
# Runs history
# --------------------------------------------------------------------------- #


class RunSummary(BaseModel):
    run_id: str
    started_at: str
    n_models: int
    n_items: int
    n_reps: int
    n_completions: int
    n_ok: int
    n_error: int
    models: list[dict[str, Any]]


# --------------------------------------------------------------------------- #
# Local probe
# --------------------------------------------------------------------------- #


class LocalProbeResult(BaseModel):
    reachable: bool
    models: list[dict[str, Any]] = Field(default_factory=list)
    error: Optional[str] = None


# --------------------------------------------------------------------------- #
# Questions
# --------------------------------------------------------------------------- #


class QuestionListItem(BaseModel):
    id: str
    type: str
    priestley_area: str
    jurisdiction: list[str]
    difficulty: str
    marks: int


class QuestionDetail(QuestionListItem):
    question_text: str
    facts: Optional[str] = None
    instructions: Optional[str] = None
    gold_answer: str
    required_authorities: list[dict[str, Any]]
    rubric: list[dict[str, Any]]
    topics: list[str]
    canary: str
