# AusLawExam-Bench Analysis Plan

This is the plan for **what we will analyse, how we will read the numbers, and
what the numbers will and will not mean** - at the current 16-item provisional
scale, and at the full 100-200 lawyer-verified scale.

## 1. The headline: fabricated-citation rate

The primary result is each model's **fabricated-citation rate**
(`fabricated / total_citations`), reported with a percentile bootstrap 95% CI
and a pairwise-permutation significance table against the other models.

### Reading the fabricated rate (important caveat)

`fabricated` is defined against a **known-authorities corpus** that is, at the
current scale, the union of the 16 items' `required_authorities` - a small set
of real Australian cases/statutes. Consequently:

- A citation that is **real but not in that small corpus is counted as
  fabricated.** So the reported rate is a **conservative upper bound** on the
  true hallucination rate, not an estimate of it.
- The bound is loosest for the open-weight slot (which cites broadly) and
  tightest for models that cite narrowly.
- **Do not read the point estimate as "X% of this model's citations are fake".**
  Read it as "at most X% (and possibly materially fewer) are invented".

### Closing the gap (corpus growth)

To turn the upper bound into an estimate, grow the corpus with a **seed list of
well-known, real Australian authorities** (e.g. the high-profile High Court
decisions and the core statutes across the Priestley 11) and classify against
that. The more real authorities in the corpus, the more the `fabricated` bucket
is reserved for genuine inventions. This is the single highest-value method
improvement and is the first item in the roadmap below.

## 2. Secondary: the rubric item score

Each completion also gets a **rubric item score** in [0,100] (judge-scored
against the item's aspect/marks breakdown), with a per-difficulty breakdown on
the leaderboard. At the prototype scale the judge is a **seeded mock ensemble**,
so these scores are a **stand-in for rubric quality**, not a calibrated
measurement. They are useful for (a) exercising the pipeline and (b) showing the
shape of the analysis; they must not be reported as final model rankings until
a real judge is wired in.

## 3. What the numbers WILL mean (16-item scale)

- That the **pipeline works end to end**: run → score → stats → leaderboard,
  offline-reproducible, real local-model inference, seeded statistics.
- A **demonstration of the reporting surface**: what a per-model fabricated
  rate, CI, and pairwise test looks like when rendered.
- A **smoke check** that the local Qwen3.8-27B slot runs and produces
  non-fabricated, on-point citations when given the required authorities in-prompt.

What the numbers will **NOT** mean at 16 items: any claim about *which model is
better at Australian law*. With 16 items and a mock judge, differences between
models are within noise; the bootstrap CIs will be wide and the permutation
tests will have little power. The leaderboard at this scale is a **layout and
method demo**, not a ranking.

## 4. What the numbers WILL mean (full 100-200, verified scale)

Once the question set is (a) grown to 100-200, (b) lawyer-verified, and (c)
paired with a real judge and a grown known-authorities corpus:

- **Fabricated-citation rate** becomes a meaningful, comparable safety metric
  across the four slots, with tight CIs and powered pairwise tests.
- **Rubric item score** becomes a calibrated measure of legal-reasoning quality,
  with by-difficulty and by-Priestley-area breakdowns.
- **Contamination flags** (canary hits) gate the leaderboard so no score rests
  on memorised items.

## 5. Analysis questions the benchmark should answer

1. Which model fabricates the fewest Australian legal authorities per answer?
2. Does fabrication concentrate in specific question types or Priestley areas?
3. How does a 27B open-weight model compare to the frontier slots on
   on-point-citation rate (not just "did it answer")?
4. Is there a quality/safety trade-off (higher rubric score but higher
   fabrication), and if so, which model?
5. How reproducible are scores across reps (variance), and across a real vs
   mock run (does wiring a key change the numbers as expected)?

## 6. Roadmap (prototype → release)

| # | Item | Status | Why it matters |
|---|---|---|---|
| 1 | Grow known-authorities corpus (seed list of real AU authorities) | **Planned** | Turns fabricated rate from an upper bound into an estimate |
| 2 | Lawyer-verify the question set to 100-200 | **Planned** | Removes the "provisional" disclaimer; prerequisite for any real claim |
| 3 | Real LLM judge (replace seeded mock ensemble) | **Planned** | Makes rubric item scores a real measurement |
| 4 | Real commercial runs (set OPENAI/ANTHROPIC/GOOGLE keys) | **Config-ready** | The 3 commercial slots currently run as seeded mocks |
| 5 | Near-duplicate / semantic-leakage check at authoring time | **Planned** | Closes the canary gap for semantic memorisation |
| 6 | Per-Priestley-area and per-difficulty slicing on the site | **Partial** | By-difficulty is on the site; by-area is in the report data |
| 7 | Publish to GitHub Pages + Hugging Face (`auslex export-hf`) | **Config-ready** | Public, citable, reproducible release |

## 7. Threats to validity and mitigations

- **Small-N inflation of significance** → report CIs and permutation p-values,
  not point estimates; do not claim model superiority at 16 items.
- **Corpus bias in fabrication** → state the upper-bound caveat prominently
  (this file, README, and the leaderboard footer).
- **Judge bias** → mock ensemble is deterministic and seeded; a real judge
  would need its own inter-rater reliability check (planned).
- **Contamination** → see `CONTAMINATION_STATEMENT.md`; canaries gate the board.
- **Reproducibility drift** → content hashing + append-only runs + recorded
  seeds/prompt version make drift detectable.

## 8. What a reader should do with the current numbers

Treat the shipped leaderboard as a **worked example of the method on 16
unverified items with one real local model and three seeded mocks**. The useful
takeaway is not "model A beats model B" but: *here is a reproducible pipeline
that will produce a defensible AU-legal benchmark once the corpus is grown, the
items are lawyer-verified, and a real judge is wired in* - and here is exactly
what the numbers will and will not mean at each stage.
