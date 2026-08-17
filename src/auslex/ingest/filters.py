"""The hard jurisdiction rule, enforced at ingestion.

The design document is strict: an item's gold answer must rely **only** on
Australian primary sources, and comparative references (UK/US/NZ) are banned
even as obiter. These filters operationalise that rule.

Note on precision over recall: this is a *lint*, not a legal oracle. It catches
unambiguous non-Australian report series and phrases (``UKHL``, ``F.3d``,
``House of Lords``). It is deliberately conservative about Australian
reporters (``CLR``, ``ALR``, ``HCA``, ``VSCA`` ...) so we do not false-positive
on legitimate AU citations.
"""

from __future__ import annotations

import re
from typing import Any

from .issues import Issue

# Unambiguous non-Australian citation markers. Extending this list is how the
# lint gets better as new corpus patterns are discovered.
NON_AU_REPORT_SERIES: list[re.Pattern[str]] = [
    # United Kingdom / England & Wales / House of Lords
    re.compile(r"\bUKHL\b"),
    re.compile(r"\bUKSC\b"),
    re.compile(r"\bUKCA\b"),
    re.compile(r"\bEWCA\b"),
    re.compile(r"\bEWKB\b"),
    re.compile(r"\bEng\s*Rep\b"),
    re.compile(r"\bAll\s*ER\b"),
    re.compile(r"\bLJNO\b"),
    # United States (federal + Supreme Court reporters, U.S. Code)
    re.compile(r"\b\d+\s+U\.S\.?\s+\d+\b"),
    re.compile(r"\bU\.S\.?\s+\d{3,4}\b"),
    re.compile(r"\bF\.\d{1,2}\s*d\b"),
    re.compile(r"\bS\.\s*Ct\.\s*\d+\b"),
    re.compile(r"\bL\.\s*Ed\.\s*\d+\b"),
    re.compile(r"\bU\.S\.C\.\b"),
    re.compile(r"\bU\.S\.\s*Code\b"),
    # New Zealand
    re.compile(r"\bNZLR\b"),
    re.compile(r"\bNZSC\b"),
    re.compile(r"\bNZCA\b"),
    re.compile(r"\bTJM\b"),
    # Canada
    re.compile(r"\bSCC\b"),
    re.compile(r"\bO\.A\.C\.\b"),
]

NON_AU_PHRASES: list[re.Pattern[str]] = [
    re.compile(r"\bUnited States\b"),
    re.compile(r"\bU\.S\. (?:Supreme )?Court\b"),
    re.compile(r"\bUS Supreme Court\b"),
    re.compile(r"\bunder US law\b"),
    re.compile(r"\bUS federal law\b"),
    re.compile(r"\bHouse of Lords\b"),
    re.compile(r"\bEnglish courts?\b"),
    re.compile(r"\bEnglish law\b"),
    re.compile(r"\bNew Zealand Courts?\b"),
    re.compile(r"\bcourts of the United Kingdom\b"),
]

# All compiled patterns with a label for reporting.
_ALL_PATTERNS: list[tuple[str, re.Pattern[str]]] = (
    [(f"report:{p.pattern}", p) for p in NON_AU_REPORT_SERIES]
    + [(f"phrase:{p.pattern}", p) for p in NON_AU_PHRASES]
)


def find_non_au(text: str) -> list[dict[str, Any]]:
    """Return every non-Australian citation/phrase marker found in ``text``.

    Each hit is ``{"pattern": str, "match": str, "start": int}``.
    """
    hits: list[dict[str, Any]] = []
    if not text:
        return hits
    for label, pattern in _ALL_PATTERNS:
        for m in pattern.finditer(text):
            hits.append({"pattern": label, "match": m.group(0), "start": m.start()})
    hits.sort(key=lambda h: h["start"])
    return hits


def _issues_for(text: str, level: str, item_id: str | None, code_prefix: str) -> list[Issue]:
    out: list[Issue] = []
    seen: set[str] = set()
    for hit in find_non_au(text):
        key = (code_prefix, hit["match"])
        if key in seen:
            continue
        seen.add(key)
        out.append(
            Issue(
                level=level,
                code=f"{code_prefix}",
                message=f"non-Australian citation/phrase {hit['match']!r} "
                f"(pattern {hit['pattern']})",
                item_id=item_id,
            )
        )
    return out


def lint_gold_answer(gold_answer: str, item_id: str | None = None) -> list[Issue]:
    """Gold answers must be AU-only — any non-AU marker is a hard error."""
    return _issues_for(gold_answer, "error", item_id, "GOLD_NON_AU")


def lint_question(question_text: str, item_id: str | None = None) -> list[Issue]:
    """A non-AU reference in the question stem is a warning (possible distractor)."""
    return _issues_for(question_text, "warning", item_id, "QUESTION_NON_AU")


def check_item(item: dict[str, Any]) -> list[Issue]:
    """Run the jurisdiction rule over one item dict (schema already enforced codes)."""
    item_id = item.get("id")
    issues: list[Issue] = []
    issues += lint_gold_answer(item.get("gold_answer", ""), item_id)
    issues += lint_question(item.get("question_text", ""), item_id)
    # required_authorities are gold-adjacent and must be AU primary sources.
    for auth in item.get("required_authorities", []):
        cite = auth.get("cite", "")
        issues += _issues_for(cite, "error", item_id, "AUTH_NON_AU")
    return issues
