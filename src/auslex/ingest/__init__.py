"""Ingestion: the hard jurisdiction rule, contamination controls, and the
schema/hash-lock gate that everything downstream trusts."""

from .issues import Issue, Report
from .filters import (
    check_item,
    find_non_au,
    lint_gold_answer,
    lint_question,
)
from .contamination import (
    check_against_corpus,
    dedup_items,
    max_overlap,
    ngrams,
    tokenize,
)
from .validate import (
    check_lock,
    compute_manifest,
    load_manifest,
    lock_items,
    validate_dataset,
    validate_item_dict,
    write_manifest,
)

__all__ = [
    "Issue",
    "Report",
    "check_item",
    "find_non_au",
    "lint_gold_answer",
    "lint_question",
    "check_against_corpus",
    "dedup_items",
    "max_overlap",
    "ngrams",
    "tokenize",
    "check_lock",
    "compute_manifest",
    "load_manifest",
    "lock_items",
    "validate_dataset",
    "validate_item_dict",
    "write_manifest",
]
