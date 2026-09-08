# AusLawExam-Bench

A reproducible benchmark of Australian legal reasoning for LLMs.

[Apache-2.0 (code) / CC BY 4.0 (data)](LICENSE) · Python >= 3.10 · 85 tests · 16 provisional questions

## Overview

AusLawExam-Bench measures how well language models reason about Australian law using exam-style questions. It scores answers on two axes: conventional rubric correctness and, more importantly, whether the model invents citations to look like it knows the law.

The benchmark runs eight model slots (GPT, Claude, Gemini, Groq, DeepSeek, Mistral, Qwen, plus a local open-weight slot) over a shared prompt template at temperature 0, extracts every citation in each answer, classifies them as real or fabricated, and publishes raw outputs plus scores so anyone can audit the numbers end to end.

**What it does not do:** it is not a legal research tool and gives no legal advice. It does not answer legal questions or verify legal propositions; the 16 shipped questions are provisional drafts that have not been reviewed by a qualified Australian lawyer.

**Maturity:** working prototype. The full pipeline runs offline with deterministic seeded mocks (set `--mock` to force); commercial model slots are config-ready and activate when API keys are supplied.

## Headline metric: fabricated-citation rate

In law, a confidently wrong citation is worse than an admitted gap. A model that invents a leading case or misstates a statute number can be just as misleading as one that writes nothing at all.

For every answer we extract citations and classify each one:

- **`on_point`** — matches one of the item's required authorities
- **`known_other`** — a real Australian authority from the corpus (correct, but not this item's specific list)
- **`fabricated`** — looks like a citation but is in neither list; an invented case or provision

```
fabricated_rate = fabricated / total_citations
```

A model can score well on rubric items and still have a high fabricated rate. That gap is what the benchmark exposes.

> With 16 questions the "known" corpus is small, so real-but-uncatalogued Australian citations count as `fabricated`. The reported rate is therefore a conservative upper bound on true hallucination, not a precise estimate. See [paper/ANALYSIS_PLAN.md](paper/ANALYSIS_PLAN.md) for how this tightens as the question set grows to 100--200 items.

## Quick start

```bash
pip install -e .
auslex run --reps 3 --mock
```

That single command runs the full pipeline offline: sends the shared prompt to every configured model (via the deterministic seeded mock runner), scores citations and rubric items, computes bootstrap CIs and permutation tests, and renders a static leaderboard HTML page. No API keys required. Without `--mock`, slots without an API key (or an unreachable local endpoint) are skipped rather than mocked.

### Other commands

```bash
# Validate question set (schema, AU-jurisdiction rule, canary presence)
auslex validate --questions data/questions/auslex.jsonl

# Hash-lock the gold set + write manifest
auslex validate --lock

# View the leaderboard locally
python3 -m http.server --directory site/<run-id> 8080

# Check local OpenAI-compatible endpoint
auslex probe-local --list

# Re-score, re-stats, rebuild site independently
auslex score runs/<run-id>
auslex stats runs/<run-id>
auslex site runs/<run-id>

# Export for Hugging Face
auslex export-hf --out export/hf
```

Run flags: `--models local,gpt` (subset of slots), `--reps N` (repeats per item; default 3), `--mock` (allow mock fallback for slots without API keys), `--out-root <dir>`, `--run-id <id>`, `--n-boot N` / `--n-perm N` (CI/permutation precision; default 10,000 each).

## Leaderboard at a glance

A mock run (16 questions, 3 reps, no API keys) shows the metric in action:

| # | Model | Mean score (95% CI) | Fabricated rate (95% CI) |
|---|-------|---------------------|--------------------------|
| 1 | gpt | 87.9 [86.5, 89.5] | 0.028 [0.000, 0.059] |
| 2 | claude | 86.9 [85.9, 88.1] | 0.052 [0.021, 0.094] |
| 3 | gemini | 86.8 [85.7, 88.0] | 0.038 [0.000, 0.090] |
| 4 | local | 80.0 [71.8, 87.0] | 0.608 [0.441, 0.771] |

The mock runner is deterministic (`seed + slot + item_id`), so anyone can reproduce these exact numbers offline -- no API keys, no network, no bills.

## Model slots

Config in [src/auslex/config.py](src/auslex/config.py). Resolution: default < config file < environment.

| Slot | Vendor | Model | Real when... | Mock profile |
|------|--------|-------|--------------|-------------|
| gpt | OpenAI | gpt-5.6 | `OPENAI_API_KEY` set | quality 0.86, fab 0.08 |
| claude | Anthropic | claude-opus-5 | `ANTHROPIC_API_KEY` set | quality 0.83, fab 0.10 |
| gemini | Google | gemini-2.0-flash | `GOOGLE_API_KEY` set | quality 0.80, fab 0.13 |
| groq | Groq | llama-3.3-70b-specdec | `GROQ_API_KEY` set | quality 0.82, fab 0.10 |
| deepseek | DeepSeek | deepseek-chat | `DEEPSEEK_API_KEY` set | quality 0.78, fab 0.12 |
| mistral | Mistral | mistral-small-latest | `MISTRAL_API_KEY` set | quality 0.75, fab 0.14 |
| qwen | Qwen | qwen2.5-72b | `DASHSCOPE_API_KEY` set | quality 0.76, fab 0.13 |
| local | OpenAI-compat | 14. Qwen3.8-27B (Q5_K_M) | `base_url` reachable | quality 0.55, fab 0.25 |

Local slot environment variables:

| Variable | Default | Note |
|----------|---------|------|
| `AUSLEX_LOCAL_BASE_URL` | `http://localhost:10000/v1` | OpenAI-compatible endpoint |
| `AUSLEX_LOCAL_MODEL` | `14. Qwen3.8-27B (Q5_K_M)` | Loaded model name |
| `AUSLEX_LOCAL_ENABLE_THINKING` | `0` | Off by default -- thinking models consume all `max_tokens` in `reasoning_content`; set to `1` to opt in |

Every completion records its `is_mock` flag end-to-end. Mock rows are labelled "synthetic" on the leaderboard and never presented as real model outputs.

## Question types & coverage

The 16 provisional items span all four exam-style formats across Priestley 11 areas:

| Type | Example question | Marks |
|------|-----------------|-------|
| Short answer | *State and explain the standard of proof in a criminal trial, and the meaning of 'beyond reasonable doubt'* | 10 |
| MCQ | *Which best states the Australian position on the duty to warn?* | 4 |
| Hypothetical | *B, a land developer, orally agreed to sell its suburban retail land to A... Advise A* | 15 |
| Essay | *Discuss, with reference to the authorities, when a person who makes a negligent misstatement can be held liable for pure economic loss* | 20 |

Jurisdictions: Cth, NSW, VIC, QLD. Areas include contract, tort, criminal, constitutional, administrative law -- and growing.

## Reproducibility

Four design principles:

1. **One shared prompt.** No per-model prompt tuning. Every model receives the identical versioned prompt template. Version recorded in `runs/<id>/meta.json`.
2. **Append-only runs.** Nothing in a run directory is ever rewritten. Tamper-evident by construction.
3. **Content-hashed items.** Items locked by SHA-256 content hash; outputs addressed by that hash. Scores are auditable against original raw outputs.
4. **Contamination canaries.** Every item embeds a global canary (`auslex:9f2c1a4e-7b3d`) and a per-item canary derived deterministically from its id. If a model reproduces either verbatim, that indicates the item was in its training data. See [data/canary.txt](data/canary.txt).

## Scoring pipeline

```
RUN  -->  SCORE  -->  STATS  -->  SITE
(model x item x rep)  (cite + rubric)  (CI + perm)  (leaderboard HTML)
```

1. **Run** -- shared prompt, temperature 0, every model x item x reps --> `records.jsonl`
2. **Score** -- extract citations, classify (`on_point` / `known_other` / `fabricated`), rubric judge per completion --> `scored.jsonl`
3. **Stats** -- percentile bootstrap 95% CIs (`n_boot=10000`), paired sign-flip permutation tests (`n_perm=10000`) --> `report.md`
4. **Site** -- render static leaderboard HTML (inline CSS, no JS) --> `index.html`

The mock judge is a seeded ensemble (`n_judges=3`), so the entire pipeline runs offline deterministically with zero configuration.

## Architecture

```
src/auslex/
  schema.py              Pydantic contract -- QuestionItem model
  config.py              Eight-model roster (config + env-driven)
  prompts.py             Single versioned prompt template
  canary.py              Contamination detection
  io.py                  JSONL IO + SHA-256 content hashing
  run/                   Orchestrator + append-only storage
  runners/               Mock, local, OpenAI, Anthropic, Google
  score/                 Citation extraction/classification + rubric judge
  stats/                 Bootstrap CIs, permutation tests, report renderer
  ingest/                Validation, AU-jurisdiction rule, dedup, hash-lock
  publish/               Static leaderboard site, HF dataset export

backend/                     FastAPI server for React+Vite UI
frontend/                    React + Vite dashboard
data/                        Question set, canaries, gold manifest
paper/                       Methodology, contamination statement, analysis plan
tools/                       author_samples.py -- regenerate provisional questions
tests/                       85 tests
```

## Tests

```bash
python3 -m pytest
```

85 tests across 12 files: schema validation, canary derivation and detection, AU-jurisdiction filters, citation extraction and classification, permutation test logic, content hashing, mock runner determinism, full mock-to-site end-to-end pipeline, CLI argument parsing, FastAPI endpoints, secrets store.

## Web UI

```bash
pip install -e ".[ui]"
auslex-ui      # --> http://localhost:8000
```

FastAPI server + React+Vite client. API keys stored in `~/.auslex-ui/keys.json` (mode 0600), never transmitted externally. No telemetry.

## Data & licensing

**Two-part license** ([LICENSE](LICENSE)):

1. Harness / code (`src/`, `tests/`, `paper/`, packaging) -- **Apache-2.0**
2. Question data -- **CC BY 4.0**

The sample items are provisional exam-style drafts that have not been checked by a qualified Australian lawyer. Gold answers and `required_authorities` may contain errors. Treat them as placeholder scaffolding, not authoritative law.

## Disclaimer

This is a benchmarking prototype, not legal advice. The shipped questions are unverified. Do not rely on any content here -- or on any model output it produces -- for real legal decisions.

## Contributing

Open issues on the repo or reach out directly. Priority areas: lawyer verification of provisional items, expansion of the citation corpus to tighten the fabricated-rate bound, and growth toward the 100--200 question target. See [paper/ANALYSIS_PLAN.md](paper/ANALYSIS_PLAN.md) for the planned analysis.
