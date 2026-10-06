"""Scoring: automated citation validation, rubric judge ensemble, and rubric
aggregation."""

from .citations import (
    Citation,
    CitationReport,
    assess_answer,
    build_known_corpus,
    extract_citations,
)
from .judge import JudgeConfig, JudgeResult, judge_answer
from .score import ModelScore, ScoreReport, score_run

__all__ = [
    "Citation",
    "CitationReport",
    "assess_answer",
    "build_known_corpus",
    "extract_citations",
    "JudgeConfig",
    "JudgeResult",
    "judge_answer",
    "ModelScore",
    "ScoreReport",
    "score_run",
]
