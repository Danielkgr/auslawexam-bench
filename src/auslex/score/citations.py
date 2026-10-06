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
# The tail is a year in brackets followed either by a volume and a report
# series ("(1988) 164 CLR 387", "[1994] 2 VR 353") or, for year-ordered reports
# and medium-neutral citations, by a series and a number ("[1932] AC 562",
# "[2021] HCA 19").
_CASE_TAIL = re.compile(
    r"[\(\[]\s*(\d{4})\s*[\)\]]\s*"
    r"(?:\d{1,4}\s+[A-Z]{2,7}(?:\s+\d+)?|[A-Z]{2,7}\s+\d+)"
)
# A party word starts with a capital and may hold "/", as in "Plaintiff S157/2002".
_PARTY = r"[A-Z][\w'&.\-/]*(?:\s*\([^)]*\))?"
_SIDE = _PARTY + r"(?:\s+" + _PARTY + r")*"
_CASE_HEAD = re.compile(r"(" + _SIDE + r"\s+v\.?\s+" + _SIDE + r")\s*$")

# Legislation citations: an "Act ... (jurisdiction) s N" or "Rules ...
# (jurisdiction) r N" anchor, with the instrument's proper name recovered from
# the words immediately before it.  Section and rule numbers may carry letters
# and dotted parts, as in "s 74H" and "r 14.28".
_STAT_ANCHOR = re.compile(
    r"\b(?:Act|Rules|Regulations?)(?:\s+\d{4})?\s*\(\s*"
    + _JUR
    + r"\s*\)\s+(?:ss?|rr?|regs?|cl)\.?\s*\d+[A-Z]{0,3}(?:\.\d+[A-Z]?)*(?:\s*\([0-9a-z]+\))*"
)


_CONNECTORS = ("and", "of", "or", "for", "the", "in", "to")


def _statute_name(prefix: str) -> str:
    """Recover the Act's proper name from the words immediately before 'Act'."""
    toks = re.findall(r"\S+", prefix)
    name: list[str] = []
    for t in reversed(toks):
        word = re.sub(r"[^A-Za-z&\-]", "", t)
        if not word:
            continue
        if word[0].isupper() or word.lower() in _CONNECTORS:
            name.append(word)
            if len(name) >= 10:
                break
        else:
            break
    words = list(reversed(name))
    while words and words[0].lower() in _CONNECTORS:
        words.pop(0)
    return " ".join(words)


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", s.lower())).strip()


@dataclass
class Citation:
    kind: str          # "case" | "statute"
    raw: str
    normalized: str
    cls: str = ""      # "on_point" | "known_other" | "fabricated", set by assess_answer


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
                {"kind": c.kind, "raw": c.raw, "class": c.cls} for c in self.citations
            ],
        }


# Markdown emphasis around a case name ("*Waltons v Maher* (1988) ...") would
# otherwise stop the party name being paired with its report.
_EMPHASIS = re.compile(r"\*{1,3}|(?<![A-Za-z0-9])_{1,3}|_{1,3}(?![A-Za-z0-9])")


# Capitalised words that open a sentence or a citation signal, not a party name.
_LEAD = {
    "see", "in", "cf", "compare", "following", "applying", "per", "also", "and",
    "but", "under", "as", "from", "by", "since", "contrast", "citing", "unlike",
    "accordingly", "therefore", "thus", "here", "there", "after", "before",
}


def _strip_lead(name: str) -> str:
    words = name.split()
    while len(words) > 1 and words[0].lower().rstrip(",") in _LEAD:
        words.pop(0)
    return " ".join(words)


def extract_citations(text: str) -> list[Citation]:
    text = _EMPHASIS.sub("", text)
    out: list[Citation] = []
    seen: set[tuple[str, str]] = set()
    cases: list[Citation] = []
    for m in _CASE_TAIL.finditer(text):
        head = _CASE_HEAD.search(text[: m.start()])
        name = _strip_lead(head.group(1)) if head else ""
        raw = ((name + " ") if name else "") + m.group(0)
        raw = re.sub(r"\s+", " ", raw).strip()
        key = ("case", _norm(raw))
        if key in seen:
            continue
        seen.add(key)
        cases.append(Citation("case", raw, _norm(raw)))
    # A bare report such as "(1988) 164 CLR 387" that repeats a fuller citation
    # in the same answer is a back-reference, not a second authority.
    named_tails = {_case_parts(c.normalized)[0] for c in cases
                   if _case_parts(c.normalized) and _case_parts(c.normalized)[1]}
    for c in cases:
        parts = _case_parts(c.normalized)
        if parts and not parts[1] and parts[0] in named_tails:
            continue
        out.append(c)
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


# Year, volume, report series, and first page at the end of a normalised case
# citation: "1988 164 clr 387", "1932 ac 562", or "2021 hca 19".
_TAIL_NORM = re.compile(r"(?:^|\s)(\d{4})\s(?:(\d{1,4})\s)?([a-z]{2,7})\s(\d+)$")
# Words that say nothing about which case is meant.
_GENERIC = {
    "v", "the", "r", "queen", "king", "re", "ex", "parte", "pty", "ltd", "limited",
    "co", "inc", "and", "of", "no", "for", "in", "a", "an",
}


def _case_parts(norm: str) -> Optional[tuple[tuple[str, ...], set[str]]]:
    """Split a normalised case citation into its report tail and party words."""
    m = _TAIL_NORM.search(norm)
    if not m:
        return None
    tail = (m.group(1), m.group(2) or "", m.group(3), m.group(4))
    return tail, {t for t in norm[: m.start()].split() if t not in _GENERIC}


def _matches(cite_norm: str, authority_norm: str) -> bool:
    if cite_norm == authority_norm:
        return True
    cite, auth = _case_parts(cite_norm), _case_parts(authority_norm)
    if cite and auth:
        # Two case citations: the report must be the same, and either side may
        # be a bare report or an abbreviated name, but different party names on
        # the same report page are a misattributed citation, not a match.
        if cite[0] != auth[0]:
            return False
        return not cite[1] or not auth[1] or bool(cite[1] & auth[1])
    # One contains the other (pinpoints / abbreviations), requiring the shorter
    # side to be substantial so we don't match on a lone party surname.
    # Containment is checked on whole tokens, so "s 18" never matches "s 181"
    # and "(1988) 164 CLR 38" never matches "(1988) 164 CLR 387".
    a, b = sorted((cite_norm, authority_norm), key=len)
    return len(a) >= 12 and f" {a} " in f" {b} "


# Seed list of real authorities that a competent answer might cite.  These are
# not tied to any single item.  Without this seed, any real citation not
# already in the item set would be miscounted as fabricated, so the seed
# tightens the fabricated-rate upper bound.  Every entry was checked by web
# search for dataset 0.2.0 (sources in data/CHANGELOG.md).  A few leading
# English authorities that Australian courts routinely cite are included,
# because citing them is not an invention.
_SEED_AUTHORITIES: list[str] = [
    # Constitutional
    "Pape v Commissioner of Taxation (2009) 238 CLR 1",
    "New South Wales v Commonwealth (1975) 135 CLR 337",
    "Commonwealth v Tasmania (1983) 158 CLR 1",
    "Queensland v Commonwealth (1989) 167 CLR 232",
    "Victoria v Commonwealth (1996) 187 CLR 416",
    "New South Wales v Commonwealth (2006) 229 CLR 1",
    # Contract
    "Waltons Stores (Interstate) Ltd v Maher (1988) 164 CLR 387",
    "Codelfa Construction Pty Ltd v State Rail Authority of NSW (1982) 149 CLR 337",
    "Central London Property Trust Ltd v High Trees House Ltd [1947] KB 130",
    "Andrews v Australia and New Zealand Banking Group Ltd (2012) 247 CLR 205",
    "Taylor v Johnson (1983) 151 CLR 422",
    "Helby v Matthews [1895] AC 471",
    # Torts
    "Rogers v Whitaker (1992) 175 CLR 479",
    'Caltex Oil (Australia) Pty Ltd v The Dredge "Willemstad" (1976) 136 CLR 529',
    "L Shaddock & Associates Pty Ltd v Parramatta City Council (No 1) (1981) 150 CLR 225",
    "Esanda Finance Corporation Ltd v Peat Marwick Hungerfords (1997) 188 CLR 241",
    "Donoghue v Stevenson [1932] AC 562",
    # Crime
    "Royall v The Queen (1991) 172 CLR 378",
    "He Kaw Teh v The Queen (1985) 157 CLR 523",
    "R v Crabbe (1985) 156 CLR 464",
    "Green v The Queen (1971) 126 CLR 28",
    # Administrative
    "Kioa v West (1985) 159 CLR 550",
    "Minister for Aboriginal Affairs v Peko-Wallsend Ltd (1986) 162 CLR 24",
    "Craig v South Australia (1995) 184 CLR 163",
    "Webb v The Queen (1994) 181 CLR 41",
    "Plaintiff S157/2002 v Commonwealth (2003) 211 CLR 476",
    "Haoucher v Minister for Immigration and Ethnic Affairs (1990) 169 CLR 648",
    "Attorney-General (NSW) v Quin (1990) 170 CLR 1",
    "Re Minister for Immigration and Multicultural Affairs; Ex parte Lam (2003) 214 CLR 1",
    # Equity and trusts
    "Giumelli v Giumelli (1999) 196 CLR 101",
    "Sidhu v Van Dyke (2014) 251 CLR 505",
    "Downsview Nominees Ltd v First City Corporation Ltd [1993] AC 295",
    # Property
    "Real Property Act 1900 (NSW) s 42",
    # Corporations
    "Corporations Act 2001 (Cth) s 181",
    "Corporations Act 2001 (Cth) s 184",
    "AWA Ltd v Daniels (1992) 7 ACSR 759",
    "Daniels v Anderson (1995) 37 NSWLR 438",
    "Australian Securities and Investments Commission v Rich (2009) 236 FLR 1",
    # Evidence
    "Evidence Act 1995 (Cth) s 58",
    "Evidence Act 1995 (Cth) s 141",
    # Civil procedure
    "Civil Procedure Act 2005 (NSW) s 56",
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
    # Normalise on entry: matching compares normalised strings, so a raw seed
    # entry such as "Craig v South Australia (1995) 184 CLR 163" would never
    # match and a real citation would be counted as fabricated.
    corpus: set[str] = {_norm(a) for a in _SEED_AUTHORITIES}
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
            c.cls = "on_point"
            report.on_point += 1
        elif _in_corpus(c, corpus):
            c.cls = "known_other"
            report.known_other += 1
        else:
            c.cls = "fabricated"
            report.fabricated += 1
    return report


def _in_corpus(cite: Citation, corpus: set[str]) -> bool:
    # A fabricated case is recognised by its invented parties: if no corpus
    # entry shares the year+reporter tail and the party stems, it's new.
    for ref in corpus:
        if _matches(cite.normalized, ref):
            return True
    return False
