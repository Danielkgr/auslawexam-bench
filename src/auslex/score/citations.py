"""Automated citation validation — the benchmark's headline metric.

For every answer we extract case and statutory citations, then classify each as:

- ``on_point``    — matches one of the item's ``required_authorities``;
- ``known_other`` — a real Australian authority from the known corpus (cited
  correctly but not on the item's required list);
- ``fabricated``  — looks like a citation but is in neither (a hallucinated
  case/provision).

``fabricated_rate`` (fabricated / total) is the headline number: it directly
measures a model's tendency to invent legal authority, the failure mode that
matters most for a legal-reasoning benchmark. It is computed identically for
mock and real runs.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Iterable, Optional

# Case citations are matched in two stages: a "tail" (year, volume, reporter)
# then a "head" (the "Party v Party" run ending just before the tail). This is
# robust to parenthesised party names such as "Mabo v Queensland (No 2)" and
# "Waltons Stores (Interstate) Ltd".
_JUR = r"(Cth|VIC|NSW|QLD|WA|SA|TAS|NT|ACT)"
_CASE_TAIL = re.compile(r"\(\s*(\d{4})\s*\)\s*(\d{1,4})\s+([A-Z]{2,6})(?:\s+\d+)?")
_PARTY = r"[A-Z][\w'&.\-]*(?:\s*\([^)]*\))?"
_SIDE = _PARTY + r"(?:\s+" + _PARTY + r")*"
_CASE_HEAD = re.compile(r"(" + _SIDE + r"\s+v\.?\s+" + _SIDE + r")\s*$")

# Statute citations: an "Act ... (jurisdiction) s N" anchor, with the Act's
# proper name recovered from the words immediately before it.
_STAT_ANCHOR = re.compile(
    r"\bAct(?:\s+\d{4})?\s*\(\s*" + _JUR + r"\s*\)\s+s\.?\s*\d+(?:\s*\(\d+\))*"
)


def _statute_name(prefix: str) -> str:
    """Recover the Act's proper name from the words immediately before 'Act'."""
    toks = re.findall(r"\S+", prefix)
    name: list[str] = []
    for t in reversed(toks):
        word = re.sub(r"[^A-Za-z&\-]", "", t)
        if not word:
            continue
        if word[0].isupper() or word.lower() in ("and", "of", "or", "for", "the", "in", "to"):
            name.append(word)
            if len(name) >= 4:
                break
        else:
            break
    return " ".join(reversed(name))


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", s.lower())).strip()


@dataclass
class Citation:
    kind: str          # "case" | "statute"
    raw: str
    normalized: str


@dataclass
class CitationReport:
    total: int = 0
    on_point: int = 0
    known_other: int = 0
    fabricated: int = 0
    citations: list[Citation] = field(default_factory=list)

    @property
    def fabricated_rate(self) -> float:
        return self.fabricated / self.total if self.total else 0.0

    @property
    def on_point_rate(self) -> float:
        return self.on_point / self.total if self.total else 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "total": self.total,
            "on_point": self.on_point,
            "known_other": self.known_other,
            "fabricated": self.fabricated,
            "fabricated_rate": round(self.fabricated_rate, 4),
            "on_point_rate": round(self.on_point_rate, 4),
            "citations": [
                {"kind": c.kind, "raw": c.raw} for c in self.citations
            ],
        }


def extract_citations(text: str) -> list[Citation]:
    out: list[Citation] = []
    seen: set[tuple[str, str]] = set()
    for m in _CASE_TAIL.finditer(text):
        head = _CASE_HEAD.search(text[: m.start()])
        raw = ((head.group(1) + " ") if head else "") + m.group(0)
        raw = re.sub(r"\s+", " ", raw).strip()
        key = ("case", _norm(raw))
        if key in seen:
            continue
        seen.add(key)
        out.append(Citation("case", raw, _norm(raw)))
    for m in _STAT_ANCHOR.finditer(text):
        name = _statute_name(text[: m.start()])
        raw = ((name + " ") if name else "") + m.group(0)
        raw = re.sub(r"\s+", " ", raw).strip()
        key = ("statute", _norm(raw))
        if key in seen:
            continue
        seen.add(key)
        out.append(Citation("statute", raw, _norm(raw)))
    return out


def _matches(cite_norm: str, authority_norm: str) -> bool:
    if cite_norm == authority_norm:
        return True
    # One contains the other (pinpoints / abbreviations), requiring the shorter
    # side to be substantial so we don't match on a lone party surname.
    a, b = sorted((cite_norm, authority_norm), key=len)
    return len(a) >= 12 and a in b


def build_known_corpus(
    items: Iterable[dict[str, Any]], extra: Optional[Iterable[str]] = None
) -> set[str]:
    """Set of normalised real-AU authorities: every dataset required_authority
    plus an optional seed list of well-known real authorities."""
    corpus: set[str] = set()
    for it in items:
        for a in it.get("required_authorities", []):
            c = a.get("cite", "")
            if c:
                corpus.add(_norm(c))
    for e in extra or []:
        corpus.add(_norm(e))
    return corpus


def assess_answer(
    item: dict[str, Any],
    text: str,
    corpus: Optional[set[str]] = None,
) -> CitationReport:
    """Classify every citation in ``text`` for one item."""
    if corpus is None:
        corpus = build_known_corpus([item])
    required = [
        _norm(a.get("cite", "")) for a in item.get("required_authorities", [])
    ]
    required = [r for r in required if r]

    report = CitationReport()
    for c in extract_citations(text):
        report.total += 1
        report.citations.append(c)
        if any(_matches(c.normalized, r) for r in required):
            report.on_point += 1
        elif _in_corpus(c, corpus):
            report.known_other += 1
        else:
            report.fabricated += 1
    return report


def _in_corpus(cite: Citation, corpus: set[str]) -> bool:
    # A fabricated case is recognised by its invented parties: if no corpus
    # entry shares the year+reporter tail and the party stems, it's new.
    for ref in corpus:
        if _matches(cite.normalized, ref):
            return True
    return False
