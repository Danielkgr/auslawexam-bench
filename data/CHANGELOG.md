# Changelog

All notable changes to the AusLawExam-Bench dataset and harness. Format
follows [Keep a Changelog](https://keepachangelog.com/); versions follow
[SemVer](https://semver.org/).

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

[0.1.0]: https://github.com/auslex/aus-legal-200-bench/compare/v0.0.0...v0.1.0
