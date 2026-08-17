# AusLawExam-Bench — Contamination Statement

## Why this matters

A benchmark is only meaningful if the models being evaluated did not already
see the questions in their training data. If a frontier model was trained on
this exact question (or a near-identical one), its score measures **memorisation
and regurgitation**, not reasoning. Contamination therefore inflates scores of
the most-data-hungry models and deflates the relative gap the benchmark exists
to measure. This statement documents how the benchmark detects and controls for
that.

## Mechanism: BIG-bench-style canary strings

We embed **canary strings** — long, distinctive, meaningless-looking tokens —
in the dataset so that if a model reproduces one verbatim in its answer, we can
conclude the corresponding item was present in its training distribution.

Two layers (see `src/auslex/canary.py` and `data/canary.txt`):

1. **Global canary** — one stable, public string, `auslex:9f2c1a4e-7b3d`,
   embedded verbatim in the dataset manifest (`data/gold/manifest.json`). It is
   **never changed** (changing it would invalidate the detection guarantee for
   already-published runs).
2. **Per-item canaries** — each item carries its own canary,
   `canary = "auslex:" + sha256("auslex:" + item_id).hexdigest()[:12]`.
   Because the derivation is deterministic from the id, per-item canaries are
   stable across regenerations and can be recomputed from the id alone. This
   lets a leak be **attributed to a specific item**, not just to the dataset.

## Detection

`auslex.canary.find_canaries(text)` scans a model answer for any string
matching `auslex:[0-9a-f]{6,40}(?:-[0-9a-f]{4,16})?`. For a (model, item) pair
we check both the **global** canary and the **per-item** canary of the item
being answered. A verbatim hit sets a **contamination flag** on that pair.

Detection is a **sufficient but not necessary** signal:

- A hit is strong *evidence* the item (or dataset) was in training data.
- A miss is *not* evidence of absence: a model could have memorised the item's
  legal content without reproducing the exact canary token. Canary detection
  catches the clearest, most mechanical form of leakage; it does not rule out
  semantic memorisation. We treat it as a floor on contamination detection,
  not a complete solution.

## What a hit means, and what we do about it

- A (model, item) pair flagged by canary is reported, not silently dropped.
- For the public leaderboard we would exclude flagged pairs from the aggregate
  scores for the affected model and note the exclusion in the run's
  provenance, so the headline number is not contaminated. (At the current 16-item
  provisional scale no model is expected to hit the canaries — this is a
  guardrail for the full release.)
- Because canaries are **deterministic from the item id**, any future
  regeneration of an item keeps the same canary, so the detection guarantee
  does not drift when the sample set is re-authored.

## Threat model and honest boundaries

- **Mechanical leakage** (the item, verbatim or near-verbatim, in training
  data): well covered by verbatim canary hits.
- **Semantic leakage** (the model has seen this fact pattern / a very similar
  question but not the canary): not directly covered by canaries. Mitigations
  for the full release: (a) per-item paraphrase canaries and (b) a
  near-duplicate check of each question against public web/legal corpora at
  authoring time. These are planned, not yet in the prototype.
- **Gold-answer leakage via the rubric:** the rubric and required authorities
  are short and distinctive; a model regurgitating the gold answer would also
  tend to reproduce the canary that sits in the same item block, which is why
  the canary is co-located with the gold content.

## Relationship to the hard jurisdiction rule

Contamination control and the AU-only jurisdiction rule (`METHODOLOGY.md` §6)
are complementary, independent gates. The jurisdiction rule keeps the *data*
Australian; canaries keep the *evaluation* free of training-set leakage. Both
run at ingestion/detection time and are reported in the run provenance.

## Summary

| Control | Catches | Limitation |
|---|---|---|
| Global canary | whole-dataset in-training | no item attribution |
| Per-item canary | specific item in-training | verbatim only; misses semantic leakage |
| Hard AU-jurisdiction lint | non-AU sources in gold data | is a lint, not a legal oracle |

The prototype ships the first two rows as working code (with 66-test coverage
of the canary layer) and the lint as the hard `GOLD_NON_AU` error. The semantic
leakage mitigations are specified here and tracked in `ANALYSIS_PLAN.md`.
