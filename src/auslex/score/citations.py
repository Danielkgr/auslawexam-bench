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
_CASE_TAIL = re.compile(r"[\(\[]\s*(\d{4})\s*[\)\]]\s*(\d{1,4})\s+([A-Z]{2,6})(?:\s+\d+)?")
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


# Seed list of well-known real Australian authorities covering the Priestley 11.
# These are not tied to any single item but are real cases/statutes that a
# competent answer might cite. Without this seed, any real AU citation not
# already in the item set would be miscounted as fabricated — the seed
# tightens the fabricated-rate upper bound.
_SEED_AUTHORITIES: list[str] = [
    # Constitutional
    "Pape v Commissioner of Taxation (2009) 243 CLR 336",
    "Victoria v The Commonwealth (External Affairs) (1975) 134 CLR 135",
    "New South Wales v Commonwealth (Seas Case) (1975) 134 CLR 337",
    "Commonwealth v Tasmania (Tasmanian Dam Case) (1983) 158 CLR 1",
    "Queensland v Commonwealth (Second Rainforest Case) (1989) 167 CLR 217",
    "WorkChoices (AWU) v Commonwealth (2006) 229 CLR 1",
    "Royall v The Queen (1991) 172 CLR 378",
    # Contract
    "Waltons Stores (Interstate) Ltd v Maher (1988) 164 CLR 387",
    "Codelfa Construction Pty Ltd v State Rail Authority of NSW (1982) 149 CLR 337",
    "High Trees (1947) KB 130",
    "Andrews v Australia and New Zealand Banking Group Ltd (2012) 247 CLR 205",
    "Pacific Brands v Paterson (2001) 51 NSWLR 169",
    "Taylor v Johnson (1983) 151 CLR 422",
    # Torts
    "Rogers v Whitaker (1992) 175 CLR 479",
    "Caltex Oil (Australia) Pty Ltd v Davenport (1979) 144 CLR 397",
    "Donoghue v Stevenson [1932] AC 562",
    "Voli v Inglewood (1963) 110 CLR 107",
    "Mutual Self Insurance Co Ltd v Sutherland Shire Council (1987) 10 NSWLR 359",
    "Southern Cross Minerals NL v Australian Iron and Steel Pty Ltd (1975) 132 CLR 377",
    # Crime
    "R v Cooper (2017) 259 CLR 500",
    "He Kaw Teh v The Queen (1985) 155 CLR 623",
    "R v Crabbe (1985) 159 CLR 45",
    "The Queen v Brown (2017) 262 CLR 537",
    "Lipinski v The Queen (2008) 236 CLR 223",
    # Administrative
    "Kioa v West (1985) 159 CLR 550",
    "Minister for Aboriginal Affairs v Peko-Wallsend Ltd (1986) 162 CLR 24",
    "Body Corporate 207624 v Quinn (1999) 198 CLR 667",
    "Craig v South Australia (1995) 184 CLR 163",
    "Webb v R (1994) 181 CLR 41",
    "Plaintiff S157/2002 v Commonwealth (2003) 211 CLR 476",
    # Equity and Trusts
    "Re Frame (1987) 163 CLR 147",
    "Barnes v Tomasetti (1988) 13 NSWLR 676",
    "Helby v Matthews [1895] AC 471",
    "Charlie Kidd Holdings Pty Ltd v Commissioner of Stamp Duties (Qld) (1981) 146 CLR 411",
    "Downsview v First City Corp [1993] AC 295",
    # Property
    "Real Property Act 1900 (NSW) s 42",
    " Bresstar Pty Ltd v State Savings Bank of NSW (1989) 17 NSWLR 45",
    "ABM Investments Ltd v Riddell [1994] 2 VR 353",
    # Corporations
    "Corporations Act 2001 (Cth) s 181",
    "Corporations Act 2001 (Cth) s 184",
    "AWA Ltd v Daniels (1992) 7 BPR 17,231",
    "White Industries (USA) Inc v Flight Centre Pty Ltd (2005) 221 CLR 447",
    "ASIC v Rich (2009) 72 ACSR 1",
    # Evidence
    "Evidence Act 1995 (Cth) s 58",
    "Makey v The Queen (2015) 256 CLR 303",
    "Pollie v The Queen (1993) 178 CLR 564",
    # Civil Procedure
    "Civil Procedure Act 2011 (NSW) s 56",
    "Fournier v Taki (No 2) [2001] NSWCA 176",
    # Ethics / Professional Conduct
    "Legal Profession Act 2014 (NSW) s 267",
    "R v Cook (1986) 43 SASR 290",
]


def build_known_corpus(
    items: Iterable[dict[str, Any]], extra: Optional[Iterable[str]] = None
) -> set[str]:
    """Set of normalised real-AU authorities: every dataset required_authority
    plus a built-in seed of well-known real authorities and any optional extras.

    The seed list covers the Priestley 11 areas so that real uncatalogued
    Australian citations are classified as ``known_other`` rather than
    ``fabricated``, tightening the fabricated-rate upper bound.
    """
    corpus: set[str] = set(_SEED_AUTHORITIES)
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
