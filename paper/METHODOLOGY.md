# AusLawExam-Bench Methodology

## 1. Objective

Measure **Australian legal reasoning** capability of frontier and open-weight
LLMs with an exam-style benchmark. The benchmark is designed to be **public,
reproducible, and auditable**: the harness, every raw model output, every score,
and the rendered leaderboard are all published, so a third party can re-run the
pipeline bit-for-bit and recompute every number.

This document describes the prototype methodology at the current scale
(16 provisional questions, 4 model slots, 3 reps). It is deliberately written
so the *method* survives the current small scale: the same pipeline will be
run unchanged when the question set grows to the 100-200 target and becomes
lawyer-verified.

## 2. Design principles

1. **Legal accuracy is not enough - fabrication is the headline failure mode.**
   In law, a confidently-wrong or invented citation is worse than an admitted
   gap. The benchmark therefore reports a **fabricated-citation rate** as its
   primary safety metric, alongside a conventional rubric item score.
2. **One shared prompt for all models.** No per-model prompt tuning, no
   per-model system prompts. Every model receives the identical, **versioned**
   prompt template. The prompt version is recorded in `runs/<id>/meta.json`.
3. **Zero temperature, multiple reps.** Generation is `temperature=0` for
   determinism; `n_reps` (default 3) repeated completions per
   (model, question) capture residual non-determinism and give per-item
   variance for the stats.
4. **Append-only, content-hashed provenance.** Runs are never rewritten.
   Items are locked by content hash; outputs are addressed by content hash.
   This makes the benchmark tamper-evident.
5. **Offline-reproducible by construction.** The three commercial slots run as
   deterministic seeded mocks when no API key is present, so the full pipeline
   (run → score → stats → leaderboard) is reproducible with zero external
   services. Real commercial runs are a config change, not a code change.

## 3. The item schema (the contract)

Each item is a validated Pydantic model (`src/auslex/schema.py`) with:

- `id` (canonical, e.g. `auslex-2026-0001`), `version` (semver),
- `type` ∈ {`hypothetical`, `short_answer`, `mcq`, `essay`},
- `jurisdiction` (list; Australian codes - `Cth`, `NSW`, `VIC`, …),
- `priestley_area` (the Priestley 11: `contract`, `tort`, `property`, `criminal`,
  `equity_trusts`, `constitutional`, `corporate`, `administrative`, `family`,
  `intellectual_property`, `environmental`),
- `question_text`, `facts`, `instructions`,
- `required_authorities` (list of typed AU authorities: case or statute),
- `gold_answer` (may reference only Australian primary sources - see §6),
- `rubric` (a list of `(aspect, marks)` that must sum to `marks`),
- `marks`, `difficulty`,
- `canary` (per-item leak-detection string - §7),
- `provenance` (tier, author, provisional flag) and `verification` (who/when,
  with a self-content-hash written at lock time).

Validation (`auslex validate`) enforces the schema, the hard AU-jurisdiction
rule, canary presence, and id/duplicate hygiene, and can hash-lock the gold
set (`--lock`).

## 4. The model roster and the run protocol

Four fixed slots (`src/auslex/config.py`): `gpt`, `claude`, `gemini`
(commercial) and `local` (open-weight, the llama.cpp / Qwen3 endpoint). Each
has an `is_mock` flag that is recorded on every completion and propagated to
the leaderboard, where mock rows are explicitly labelled "synthetic".

For each (model, question, rep):

- The single shared prompt is built (`src/auslex/prompts.py`).
- The response is recorded with tokens, cost, latency, and (where the
  provider supplies it) the system fingerprint.
- A completion is scored only if it is non-empty (`ok = resp.ok and
  bool(resp.text)`); empty answers (e.g. a thinking model that spent its whole
  budget in reasoning) are flagged rather than scored.

### Thinking models

Some open-weight models (Qwen3 in particular) are *thinking* models: with
chain-of-thought enabled they fill `max_tokens` with `reasoning_content` and
return an empty `content`. The local runner therefore disables thinking by
default via `chat_template_kwargs: {"enable_thinking": false}`, controlled by
`AUSLEX_LOCAL_ENABLE_THINKING` (default off). This keeps the local slot
comparable to the commercial slots (which return a normal answer). See the
README "Thinking models" note.

## 5. Scoring

Each non-empty completion is scored two ways, independently:

### 5.1 Citation validation (the headline metric)

`src/auslex/score/citations.py` extracts case and statutory citations from the
answer and classifies each against a **known-authorities corpus**:

- `on_point` - in the item's own `required_authorities`;
- `known_other` - a real AU authority elsewhere in the corpus;
- `fabricated` - in neither.

The corpus is built by unioning every item's `required_authorities`
(`build_known_corpus`), so at 16 items it is a small set of real authorities.
`fabricated_rate = fabricated / total_citations` is the headline number.

> **Limitation (restated, and central to interpretation).** Because the corpus
> is small, a real-but-uncatalogued AU citation is counted as fabricated. The
> rate is therefore an *upper bound* on the true hallucination rate, not an
> estimate of it. The bound tightens as the corpus grows. See
> `ANALYSIS_PLAN.md` §"Reading the fabricated rate".

### 5.2 Rubric judge (the item score)

`src/auslex/score/judge.py` scores the answer against the item's rubric. The
production path calls an LLM judge; the prototype ships a **seeded mock
ensemble** (default `n_judges=3`, per-judge order randomization, seeded) so the
pipeline runs offline and the judge stage is deterministic. Each completion
gets an `item_score` in [0, 1] and a per-rubric-aspect breakdown.

## 6. The hard jurisdiction rule

An item's **gold answer** may rely only on Australian primary sources.
`src/auslex/ingest/filters.py` is a conservative *lint* over the gold answer
text:

- a **non-AU citation** (US/UK/NZ reporter, or a "United States", "England and
  Wales", "House of Lords", etc. phrase) → **hard error** `GOLD_NON_AU`;
- a non-AU mention in the **question stem** → **warning** `QUESTION_NON_AU`;
- a non-AU citation in `required_authorities` → **hard error** `AUTH_NON_AU`.

It is deliberately conservative about Australian reporters (e.g. it will not
flag `CLR`, `VLR`, `Qld`), so it is a gate against obvious cross-jurisdiction
contamination, not a legal oracle.

## 7. Contamination control

See `CONTAMINATION_STATEMENT.md`. In short: every item carries a global
canary plus a deterministic per-item canary; if an evaluated model reproduces
either verbatim, that is evidence of training-data leakage and the affected
(question, model) pair is flagged.

## 8. Statistics

`src/auslex/stats/` computes, all **seeded and reproducible**:

- **Percentile bootstrap 95% CIs** for the question-level mean item score and
  the fabricated-citation rate, per model (`n_boot` resamples of items).
- **Paired sign-flip permutation tests** for each model pair over the shared
  question set: the observed mean difference is compared against the
  distribution of sign-flipped differences; `p = (n_extreme + 1) /
  (n_perm + 1)`.

The report (`stats/<id>/{stats.json,report.md}`) contains the ordered
leaderboard, per-difficulty breakdown, and the pairwise significance table.

## 9. Reproducibility checklist

Given a run dir, the following are fully determined and re-derivable:

- the exact prompt template + version (`meta.json`),
- the exact item set + content hashes (`meta.json`),
- the generation config (temperature, max_tokens, seeds),
- every raw provider payload (`raw/`),
- every score (`scores/`),
- every statistic and p-value (seed recorded in `meta.json`).

`auslex score` / `auslex stats` / `auslex site` can re-derive scores, stats,
and the site from an existing run without touching the model APIs.

## 10. Scope and known limitations (prototype)

- **16 provisional, unverified questions.** Not lawyer-verified; not
  representative of the target 100-200.
- **Small known-authorities corpus** → fabricated rate is an upper bound.
- **Mock judge** (seeded ensemble) rather than a real LLM judge → item scores
  are a stand-in for judge quality, not a calibrated rubric measurement.
- **Mock commercial slots** when no key is set → three of four rows are
  synthetic (and labelled as such).
- **No cross-model judge** - the judge is per-item, not a comparative ranking.

The plan to close each of these, and what the numbers will mean once they are
closed, is in `ANALYSIS_PLAN.md`.
