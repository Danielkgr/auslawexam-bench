# Changelog

All notable changes to the AusLawExam-Bench dataset and harness. Format
follows [Keep a Changelog](https://keepachangelog.com/); versions follow
[SemVer](https://semver.org/).

## [0.2.0] - 2026-10-06

Every `required_authorities` citation in the 16 items, and every entry in the
seed corpus in `src/auslex/score/citations.py`, was checked by web search
against court, legislation-register, law-firm, journal, and case-summary
sources.  An authority was replaced only by one that was verified and that
supports the same proposition; otherwise it was removed.  Where a gold answer
relied on a changed authority, its text was adjusted minimally.  Every item
stays `provisional: true`, and twelve items move to version 0.2.0.

### Fixed in the answer key

| Item | Was | Now | Why |
|---|---|---|---|
| 0004 | Caltex Oil (Australia) Pty Ltd v Davenport (1979) 144 CLR 397 | L Shaddock & Associates Pty Ltd v Parramatta City Council (No 1) (1981) 150 CLR 225, and Caltex Oil (Australia) Pty Ltd v The Dredge "Willemstad" (1976) 136 CLR 529 | No such case found.  Shaddock ([1981] HCA 59) is the High Court negligent-misstatement authority the gold answer describes.  Caltex v Willemstad ([1976] HCA 65) is the pure economic loss authority for the indeterminate-liability point |
| 0005 | R v Cooper (2017) 259 CLR 500 | Green v The Queen (1971) 126 CLR 28, and Evidence Act 1995 (Cth) s 141 | No such case found (Palmer v Ayres begins at 259 CLR 478).  Green ([1971] HCA 55) is the leading case on directing a jury about reasonable doubt, and it contradicts the gold answer's "moral certainty" gloss, which was replaced |
| 0006 | He Kaw Teh v The Queen (1985) 155 CLR 623 | He Kaw Teh v The Queen (1985) 157 CLR 523 | Misreported citation ([1985] HCA 43) |
| 0007 | Pape v Commissioner of Taxation (2009) 243 CLR 336 | Pape v Commissioner of Taxation (2009) 238 CLR 1 | Misreported citation ([2009] HCA 23), also in the question text.  The gold answer said the payments rested on s 61 read with s 81; the Court held s 81 is not a spending power and upheld the Act under s 51(xxxix) with s 61, so that description was corrected |
| 0008 | Victoria v The Commonwealth (External Affairs) (1975) 134 CLR 135 | Commonwealth v Tasmania (1983) 158 CLR 1 | No such case found (134 CLR 81 is the Petroleum and Minerals Authority case).  The Tasmanian Dam Case ([1983] HCA 21) upheld treaty-implementing legislation on a subject otherwise within State competence.  The question text named the invented case and now names this one |
| 0010 | Minister for Aboriginal Affairs v Peko-Wallsend Ltd (1986) 162 CLR 24 | Haoucher v Minister for Immigration and Ethnic Affairs (1990) 169 CLR 648, and Attorney-General (NSW) v Quin (1990) 170 CLR 1 | Peko-Wallsend is a relevant-considerations case, not a legitimate-expectations case.  Quin holds that a legitimate expectation gives no substantive right, so option B no longer says the decision-maker must act in accordance with its representations |
| 0011 | Re Frame (1987) 163 CLR 147 | Giumelli v Giumelli (1999) 196 CLR 101 | No such case found.  Giumelli ([1999] HCA 10), an appeal from Western Australia, concerns a promise of family farm land relied on to the son's detriment |
| 0012 | Real Property Act 1900 (NSW) s 42 | Real Property Act 1900 (NSW) ss 74H and 74P | Section 42 is indefeasibility.  Caveats are lodged under s 74F, take effect under s 74H, and s 74P gives compensation for a caveat lodged without reasonable cause |
| 0013 | Corporations Act 2001 (Cth) ss 181 and 184 | Corporations Act 2001 (Cth) ss 181, 182 and 183 | The civil duties not to misuse position and information are ss 182 and 183; s 184 is the criminal offence for dishonest breach.  The gold answer also called s 191 the related-party regime; s 191 is the material-personal-interest notice duty, with s 195 for public companies |
| 0014 | Evidence Act 1995 (Cth) s 58 | Evidence Act 1995 (Cth) s 59 | Section 58 is inferences as to relevance; s 59 is the hearsay rule, whose wording the gold answer now quotes |
| 0015 | Civil Procedure Act 2011 (NSW) s 56 | Uniform Civil Procedure Rules 2005 (NSW) r 14.28 | The Act is the Civil Procedure Act 2005 (NSW), and its s 56 is the overriding purpose.  Striking out a pleading is r 14.28, and dismissing proceedings as frivolous or vexatious is r 13.4, so the question and option B now track r 14.28 |
| 0016 | Legal Profession Act 2014 (NSW) s 267 | Legal Profession Uniform Law Australian Solicitors' Conduct Rules 2015 (NSW) r 9 | No such Act; NSW applies the Legal Profession Uniform Law.  Rule 9.1 is the solicitor's confidentiality duty and r 9.2 lists the exceptions the gold answer now follows |

Rubric criterion names, key issues, and topics that named a corrected section
were renamed to match (for example `states_s_58_hearsay_rule` became
`states_s_59_hearsay_rule`).  Marks are unchanged.

### Fixed in the seed corpus

Removed because no source could be found: Pacific Brands v Paterson (2001) 51
NSWLR 169, Mutual Self Insurance Co Ltd v Sutherland Shire Council (1987) 10
NSWLR 359, Southern Cross Minerals NL v Australian Iron and Steel Pty Ltd
(1975) 132 CLR 377, Voli v Inglewood (1963) 110 CLR 107, R v Cooper (2017) 259
CLR 500, The Queen v Brown (2017) 262 CLR 537, Lipinski v The Queen (2008) 236
CLR 223, Body Corporate 207624 v Quinn (1999) 198 CLR 667, Re Frame (1987)
163 CLR 147, Barnes v Tomasetti (1988) 13 NSWLR 676, Charlie Kidd Holdings Pty
Ltd v Commissioner of Stamp Duties (Qld) (1981) 146 CLR 411, Bresstar Pty Ltd v
State Savings Bank of NSW (1989) 17 NSWLR 45, ABM Investments Ltd v Riddell
[1994] 2 VR 353, White Industries (USA) Inc v Flight Centre Pty Ltd (2005) 221
CLR 447, Makey v The Queen (2015) 256 CLR 303, Pollie v The Queen (1993) 178
CLR 564, Fournier v Taki (No 2) [2001] NSWCA 176, R v Cook (1986) 43 SASR 290,
Caltex Oil (Australia) Pty Ltd v Davenport, Victoria v The Commonwealth
(External Affairs), and Legal Profession Act 2014 (NSW) s 267.

Corrected: Pape to 238 CLR 1, the Seas and Submerged Lands Case to New South
Wales v Commonwealth (1975) 135 CLR 337, the Rainforest case to Queensland v
Commonwealth (1989) 167 CLR 232, WorkChoices to New South Wales v Commonwealth
(2006) 229 CLR 1, R v Crabbe to (1985) 156 CLR 464, AWA Ltd v Daniels to (1992)
7 ACSR 759, ASIC v Rich to (2009) 236 FLR 1, High Trees to Central London
Property Trust Ltd v High Trees House Ltd [1947] KB 130, Downsview to Downsview
Nominees Ltd v First City Corporation Ltd [1993] AC 295, and the Civil
Procedure Act to 2005.

Added after verification: Caltex Oil v The Dredge "Willemstad", L Shaddock &
Associates v Parramatta City Council (No 1), Esanda Finance Corporation Ltd v
Peat Marwick Hungerfords (1997) 188 CLR 241, Green v The Queen, Giumelli v
Giumelli, Sidhu v Van Dyke (2014) 251 CLR 505, Haoucher, Quin, Re Minister for
Immigration and Multicultural Affairs; Ex parte Lam (2003) 214 CLR 1, Victoria
v Commonwealth (1996) 187 CLR 416, and Daniels v Anderson (1995) 37 NSWLR 438.

### Added

- A real hash lock.  `auslex validate --lock` stamps each item's SHA-256
  content hash into `verification.hash` and writes `data/gold/manifest.json`,
  and `auslex validate` now fails on any item that changed after the lock.
  The 16 items are locked at this version.

### Removed

- `tools/author_samples.py` and the `auslex author` command.  The script had
  already drifted from the shipped data and still held the invented
  authorities, so running it would have overwritten the corrected set.  The
  JSONL file is now the source of truth and changes are recorded here.

### Open questions for the lawyer review

These were not changed, because the search evidence did not settle them.

- 0006 keys option B (the accused may bear the legal burden, read down to the
  least onerous burden).  He Kaw Teh holds that an accused who raises honest
  and reasonable mistake bears only an evidential burden, which is closer to
  option A.  The keyed answer needs review.
- 0001 says the remedy is compensation for detriment rather than specific
  performance.  The Waltons remedy should be checked against the judgment.
- 0009 attributes both the bias rule and the hearing rule to Kioa v West, which
  is a hearing-rule case.

## [0.1.0] - 2026-01-01

### Added

- Harness scaffold: item schema (`schema.py`), ingestion + validation
  (schema / jurisdiction / canary / dedup), model runners (local OpenAI-compatible
  + keyless commercial slots with a seeded mock fallback), and the two-stage
  citation extractor (`score/citations.py`).
- **Provisional sample question set (16 items)** at `data/questions/auslex.jsonl`,
  authored by `tools/author_samples.py`. Every item is `provisional: true`,
  `tier: B`, and requires verification by a qualified Australian lawyer before
  external use. Coverage:
  - All four item types: `hypothetical` (3), `short_answer` (6), `mcq` (5),
    `essay` (2).
  - All 11 named Priestley subjects: contract, torts, crime, constitutional,
    admin, equity_trusts, property, corporations, evidence, civil_procedure,
    ethics.
  - Difficulty spread: pass (6), credit (7), distinction (2), high_distinction (1).
- Scoring + stats + publishing layers:
  - Automated citation validation (fabricated-citation rate is the headline
    metric).
  - Order-randomized LLM-judge rubric scoring (seeded mock judge for keyless
    runs; real judge config-ready).
  - Pure-Python seeded statistics: question-level bootstrap 95% CIs, paired
    sign-flip permutation tests, per-topic / per-difficulty breakdowns.
  - Leaderboard site builder (`publish/site.py`) and offline Hugging Face export
    (`publish/export_hf.py`).
- Canary + integrity controls: global canary (`data/canary.txt`), deterministic
  per-item canaries, and append-only run directories.

### Status / limitations

- **Provisional data.** The 16 sample items are realistic exam-style questions
  written to exercise the harness; they are NOT lawyer-verified and are labelled
  accordingly. They are placeholders pending the lawyer-verification gate.
- **Keyless commercial slots are mocked.** Without API keys, the GPT / Claude /
  Gemini slots use a deterministic seeded mock so the end-to-end pipeline is
  reproducible and the leaderboard can be rendered. Real API runners are
  config-ready and activate when keys are supplied.
- **Open-weight slot is real.** The local `llama.cpp` slot runs a genuine local
  model (Qwen3.8-27B at `http://localhost:10000/v1` in this prototype).

[0.1.0]: https://github.com/Danielkgr/auslawexam-bench/compare/v0.0.0...v0.1.0
