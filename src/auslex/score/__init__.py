"""Scoring: automated citation validation, rubric judge ensemble, rubric
aggregation, and human calibration (Cohen's kappa)."""

from .citations import (
    Citation,
    CitationReport,
    assess_answer,
    build_known_corpus,
    extract_citations,
)
from .human import (
    BANDS,
    Agreement,
    band,
    cohen_kappa,
    kappa_between_bands,
)
from .judge import JudgeConfig, JudgeResult, judge_answer
from .score import ModelScore, ScoreReport, score_run

__all__ = [
    "Citation",
    "CitationReport",
    "assess_answer",
    "build_known_corpus",
    "extract_citations",
    "BANDS",
    "Agreement",
    "band",
    "cohen_kappa",
    "kappa_between_bands",
    "JudgeConfig",
    "JudgeResult",
    "judge_answer",
    "ModelScore",
    "ScoreReport",
    "score_run",
]
