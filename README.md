<div align="center">

# AusLawExam-Bench

### A reproducible benchmark of Australian legal reasoning for LLMs, scored on how often a model invents a citation

![16 provisional questions](https://img.shields.io/badge/questions-16_provisional-9a6700?style=for-the-badge) ![85 tests](https://img.shields.io/badge/tests-85-0969da?style=for-the-badge) ![8 model slots](https://img.shields.io/badge/model_slots-8-0969da?style=for-the-badge) ![runs offline on mocks](https://img.shields.io/badge/runs-offline-8250df?style=for-the-badge) ![Apache-2.0 code, CC BY 4.0 data](https://img.shields.io/badge/licence-Apache--2.0_%2F_CC_BY_4.0-57606a?style=for-the-badge)

</div>

<br>

> In law, a confidently wrong citation is worse than an admitted gap.  A model that invents a leading case or misstates a section number can mislead as badly as one that writes nothing at all.  This benchmark checks every citation a model produces against known Australian authority, so **a model that scores well on the rubric while inventing cases shows up as exactly that**.

<br>

## What it is

AusLawExam-Bench puts exam-style questions on Australian law to eight model slots, one each for GPT, Claude, Gemini, Groq, DeepSeek, Mistral, and Qwen, plus a local open-weight slot.  Every model gets the same versioned prompt at temperature 0.  The harness extracts each citation from each answer, classifies it as real or fabricated, scores the answer against a rubric, and publishes the raw outputs next to the scores so anyone can audit a number end to end.

> [!CAUTION]
> This is a benchmarking prototype and gives no legal advice.  It does not answer legal questions or verify legal propositions.  The 16 shipped questions are provisional drafts that no qualified Australian lawyer has reviewed, and their gold answers and required authorities may contain errors.  Do not rely on them, or on any model output the benchmark produces, for a real legal decision.

It is a working prototype.  The full pipeline runs offline on deterministic seeded mocks, and each commercial slot switches on when its API key is present.

<br>

## Results

No real model has been scored yet.  The table below comes from a mock run of 16 questions and three repetitions with no API keys, so **every number in it is synthetic**.  It shows the metric working and says nothing about any real model.

| # | Slot | Mean score (95% CI) | Fabricated rate (95% CI) |
|:--:|---|---|---|
| 1 | gpt | 87.9 [86.5, 89.5] | 0.028 [0.000, 0.059] |
| 2 | claude | 86.9 [85.9, 88.1] | 0.052 [0.021, 0.094] |
| 3 | gemini | 86.8 [85.7, 88.0] | 0.038 [0.000, 0.090] |
| 4 | local | 80.0 [71.8, 87.0] | 0.608 [0.441, 0.771] |

The mock runner seeds on the run seed, the slot, and the item id, so anyone can reproduce these exact numbers offline without an API key.  Every completion carries an `is_mock` flag from end to end, and the leaderboard labels mock rows as synthetic rather than presenting them as model output.

<br>

## How it works

### The headline metric

For every answer, the harness extracts the citations and puts each one in a class.

| Class | Meaning |
|---|---|
| `on_point` | Matches one of the item's required authorities |
| `known_other` | A real Australian authority from the corpus, but not one on this item's list |
| `fabricated` | Looks like a citation but appears in neither list, which makes it an invented case or provision |

```text
fabricated_rate = fabricated / total_citations
```

A model can score well on rubric items and still have a high fabricated rate.  That gap is what the benchmark exists to expose.

> [!WARNING]
> With 16 questions the known corpus is small, so a real Australian citation that is not yet catalogued counts as `fabricated`.  The reported rate is a conservative upper bound on true hallucination rather than a precise estimate.  [paper/ANALYSIS_PLAN.md](paper/ANALYSIS_PLAN.md) sets out how the bound tightens as the question set grows toward 100 to 200 items.

### Scoring pipeline

| Stage | Command | What happens | Output |
|---|---|---|---|
| **Run** | `auslex run` | Sends the shared prompt at temperature 0 for every model, item, and repetition | `records.jsonl` |
| **Score** | `auslex score` | Extracts and classifies citations, then applies the rubric judge to each completion | `scored.jsonl` |
| **Stats** | `auslex stats` | Computes percentile bootstrap 95% confidence intervals and paired sign-flip permutation tests, 10,000 resamples each | `report.md` |
| **Site** | `auslex site` | Renders a static leaderboard page with inline CSS and no JavaScript | `index.html` |

The mock judge is a seeded ensemble of three judges, so the whole pipeline runs offline and deterministically with no configuration.

### Reproducibility

| Principle | What it means |
|---|---|
| **One shared prompt** | No model gets its own prompt tuning.  Every model receives the identical versioned template, and `runs/<id>/meta.json` records the version. |
| **Append-only runs** | Nothing in a run directory is ever rewritten, so any tampering would show. |
| **Content-hashed items** | Each item is locked by its SHA-256 content hash and each output is addressed by that hash, so every score can be audited against the raw output it came from. |
| **Contamination canaries** | Every item carries a global canary (`auslex:9f2c1a4e-7b3d`) and a per-item canary derived from its id.  A model that reproduces either one verbatim has probably seen the item in training.  See [data/canary.txt](data/canary.txt). |

<br>

## Quick start

```bash
pip install -e .
auslex run --reps 3 --mock
```

That one command runs the whole pipeline offline.  It sends the shared prompt to every configured slot through the seeded mock runner, scores citations and rubric items, computes the intervals and permutation tests, and renders a static leaderboard page.  No API keys are needed.  Without `--mock`, a slot with no API key, or a local endpoint that does not answer, is skipped rather than mocked.

```bash
python3 -m pytest
```

The 85 tests across 12 files cover schema validation, canary derivation and detection, the Australian-jurisdiction filters, citation extraction and classification, the permutation test, content hashing, mock runner determinism, a full run from mock to site, CLI parsing, the FastAPI endpoints, and the secrets store.

<br>

## Usage

### Commands

```bash
# Validate the question set (schema, Australian-jurisdiction rule, canary presence)
auslex validate --questions data/questions/auslex.jsonl

# Hash-lock the gold set and write the manifest
auslex validate --lock

# View the leaderboard locally
python3 -m http.server --directory site/<run-id> 8080

# Check a local OpenAI-compatible endpoint
auslex probe-local --list

# Re-score, re-run the statistics, or rebuild the site on their own
auslex score runs/<run-id>
auslex stats runs/<run-id>
auslex site runs/<run-id>

# Export for Hugging Face
auslex export-hf --out export/hf
```

### Run flags

| Flag | Effect | Default |
|---|---|---|
| `--models local,gpt` | Runs a subset of slots | All slots |
| `--reps N` | Repetitions per item | `3` |
| `--mock` | Falls back to the mock runner for any slot with no API key | Off |
| `--out-root <dir>` | Where runs are written | `runs/` |
| `--run-id <id>` | Names the run | `auslex-` and a UTC timestamp |
| `--n-boot N`, `--n-perm N` | Bootstrap and permutation resamples | `10000` each |

### Web UI

```bash
pip install -e ".[ui]"
auslex-ui      # serves http://localhost:8000
```

The UI is a FastAPI server with a React and Vite client.  A built copy of the client ships in `src/auslex/publish/assets`, so Node.js is not needed to run it.  After changing `frontend/`, run `npm install` and `npm run build` there, and the server serves that build in place of the shipped copy.  Copy `frontend/dist` over `src/auslex/publish/assets` to update the shipped copy.  API keys are stored in `~/.auslex-ui/keys.json` with mode 0600 and are never transmitted externally.  There is no telemetry.

<br>

## Reference

### Model slots

Configuration lives in [src/auslex/config.py](src/auslex/config.py).  A config file overrides the defaults, and the environment overrides both.

| Slot | Vendor | Model | Live when | Mock profile |
|---|---|---|---|---|
| gpt | OpenAI | gpt-5.6 | `OPENAI_API_KEY` is set | quality 0.86, fab 0.08 |
| claude | Anthropic | claude-opus-5 | `ANTHROPIC_API_KEY` is set | quality 0.83, fab 0.10 |
| gemini | Google | gemini-2.0-flash | `GOOGLE_API_KEY` is set | quality 0.80, fab 0.13 |
| groq | Groq | llama-3.3-70b-specdec | `GROQ_API_KEY` is set | quality 0.82, fab 0.10 |
| deepseek | DeepSeek | deepseek-chat | `DEEPSEEK_API_KEY` is set | quality 0.78, fab 0.12 |
| mistral | Mistral | mistral-small-latest | `MISTRAL_API_KEY` is set | quality 0.75, fab 0.14 |
| qwen | Qwen | qwen2.5-72b | `DASHSCOPE_API_KEY` is set | quality 0.76, fab 0.13 |
| local | OpenAI-compatible | 14. Qwen3.8-27B (Q5_K_M) | `base_url` answers | quality 0.55, fab 0.25 |

### Local slot

| Variable | Default | Purpose |
|---|---|---|
| `AUSLEX_LOCAL_BASE_URL` | `http://localhost:10000/v1` | OpenAI-compatible endpoint |
| `AUSLEX_LOCAL_MODEL` | `14. Qwen3.8-27B (Q5_K_M)` | Loaded model name |
| `AUSLEX_LOCAL_ENABLE_THINKING` | `0` | Off by default, because a thinking model spends its whole `max_tokens` budget in `reasoning_content`.  Set it to `1` to opt in. |

### Question set

The 16 provisional items cover all four exam formats across Priestley 11 areas, in Commonwealth, New South Wales, Victorian, and Queensland law.  The areas so far include contract, tort, criminal, constitutional, and administrative law.

| Type | Example question | Marks |
|---|---|:--:|
| Short answer | *State and explain the standard of proof in a criminal trial, and the meaning of 'beyond reasonable doubt'* | 10 |
| Multiple choice | *Which best states the Australian position on the duty to warn?* | 4 |
| Hypothetical | *B, a land developer, orally agreed to sell its suburban retail land to A [...] Advise A* | 15 |
| Essay | *Discuss, with reference to the authorities, when a person who makes a negligent misstatement can be held liable for pure economic loss* | 20 |

<br>

## Layout

```text
src/auslex/
  schema.py        Pydantic contract for the QuestionItem model
  config.py        Eight-slot roster, driven by config and environment
  prompts.py       The single versioned prompt template
  canary.py        Contamination detection
  io.py            JSONL reading and writing, SHA-256 content hashing
  run/             Orchestrator and append-only storage
  runners/         Mock, local, OpenAI, Anthropic, and Google runners
  score/           Citation extraction and classification, rubric judge
  stats/           Bootstrap intervals, permutation tests, report renderer
  ingest/          Validation, Australian-jurisdiction rule, dedup, hash-lock
  publish/         Static leaderboard site, Hugging Face export, and the built web client

backend/           FastAPI server for the web UI
frontend/          React and Vite dashboard
data/              Question set, canaries, gold manifest
paper/             Methodology, contamination statement, analysis plan
tools/             author_samples.py, which regenerates the provisional questions
tests/             85 tests
```

<br>

## Contributing

Open an issue, or get in touch directly.  The priorities are lawyer verification of the provisional items, a larger citation corpus to tighten the fabricated-rate bound, and growth toward the target of 100 to 200 questions.  [paper/ANALYSIS_PLAN.md](paper/ANALYSIS_PLAN.md) sets out the planned analysis.

<br>

## Licence

The licence has two parts.  The harness and code (`src/`, `tests/`, `paper/`, and the packaging) are under Apache-2.0.  The question data is under CC BY 4.0.  See [LICENSE](LICENSE).
