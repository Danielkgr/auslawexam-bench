"""Reproducible statistics: seeded bootstrap CIs, paired permutation tests,
and the per-run report writer."""

from .bootstrap import Interval, bootstrap_ci
from .permutation import PermutationResult, paired_permutation
from .report import (
    build_report,
    load_scored,
    render_markdown,
    write_report,
)

__all__ = [
    "Interval",
    "bootstrap_ci",
    "PermutationResult",
    "paired_permutation",
    "build_report",
    "load_scored",
    "render_markdown",
    "write_report",
]
