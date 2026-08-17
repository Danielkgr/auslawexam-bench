# AusLawExam-Bench (`auslex`)

A public, reproducible benchmark of **Australian legal reasoning**.

The goal is a dataset of 100–200 exam-style Australian-law questions with
lawyer-verified gold answers, run over a fixed roster of frontier models
(GPT, Claude, Gemini) **plus one open-weight model**, with the full harness,
raw outputs, and scores published so the benchmark is auditable and
reproducible end to end.

> **Status: working prototype.** This repository ships a complete, runnable
> harness, a small **provisional** sample question set (16 items, all four
> question types, across the Priestley 11), and a working end-to-end demo that
> produces real scores and a rendered leaderboard. The sample items are
> **flagged `provisional` and are NOT lawyer-verified** — they are plausible
> exam-style drafts that require professional verification before the
> benchmark makes any claims about real models. See the [Disclaimer](#disclaimer).

---

## What makes a legal benchmark different

The headline metric is **not** just "did the model get the right answer". For
legal reasoning the single most dangerous failure mode is **inventing
authority** — citing a case or statute that does not exist, or misstating one.
A model that fabricates a "leading case" is unusable in practice, so the
benchmark's primary number is the **fabricated-citation rate**:

For every answer we extract each case/statutory citation and classify it as:

| Class | Meaning |
|---|---|
| `on_point` | matches one of the item's own `required_authorities` |
| `known_other` | a real Australian authority from the curated corpus (right, but not this item's required list) |
| `fabricated` | looks like a citation but is in neither — an invented case/provision |

`fabricated_rate = fabricated / total_citations` is reported per model with a
bootstrap 95% CI, and is the number the leaderboard is primarily ordered by
alongside the rubric item score.

> **Honest limitation.** The "known" corpus is built from the union of every
> item's `required_authorities` (16 items → a small set of ~16 distinct
> real authorities). Because that set is small, **anything not in it counts as
> `fabricated`** — so a *real* Australian citation that simply isn't in the
> catalog is miscounted as fabricated. The reported rate is therefore a
> **conservative upper bound on true hallucination**, not a precise estimate.
> Growing the catalog (e.g. a seed list of well-known real AU authorities)
> tightens the bound. This is documented in
> [`paper/ANALYSIS_PLAN.md`](paper/ANALYSIS_PLAN.md).

---

## Layout

```
auslex/
├── src/auslex/
│   ├── schema.py            # pydantic item schema (the contract)
│   ├── canary.py            # BIG-bench-style canary generation + leak detection
│   ├── config.py            # the four-model roster (config- + env-driven)
│   ├── prompts.py           # the single shared prompt template (versioned)
│   ├── io.py                # JSONL IO + content hashing
│   ├── ingest/              # validation, the hard AU-jurisdiction rule, dedup, hash-lock
│   ├── runners/             # base + mock / local / openai / anthropic / google
│   ├── run/                 # orchestrator (run) + append-only storage
│   ├── score/               # citation validation + rubric judge (mock ensemble)
│   ├── stats/               # percentile bootstrap CI + paired permutation test + report
│   └── publish/             # static leaderboard site + offline HF export
├── data/
│   ├── questions/auslex.jsonl   # the (provisional) sample question set — 16 items
│   ├── canary.txt               # the public canary strings + how detection works
│   └── CHANGELOG.md
├── paper/
│   ├── METHODOLOGY.md
│   ├── CONTAMINATION_STATEMENT.md
│   └── ANALYSIS_PLAN.md
├── tools/author_samples.py      # regenerates the provisional sample set
├── tests/                          # 66 tests
└── runs/ scores/ stats/ site/     # produced by `auslex run` (gitignored)
```

---

## Install

Requires **Python ≥ 3.10** (developed on 3.14). Single third-party dependency:
`pydantic` (everything else is stdlib).

```bash
pip install -e .            # harness (pydantic only)
pip install -e .[dev]       # + pytest
```

> On this machine use `python3` (there is no `python` on PATH).

The benchmark is **fully runnable offline**: the three commercial slots fall
back to a deterministic, seeded **mock** runner when no API key is present, so
the whole pipeline (run → score → stats → leaderboard) works with zero
configuration. Real commercial runs are config-ready — just set the key.

---

## How to run

The canonical command runs the entire pipeline in one process:

```bash
auslex run --reps 3
```

That single command:

1. **run** — sends the single shared prompt (temperature 0) to every configured
   model × every question × `--reps` times, writing an append-only,
   content-hash-addressed transcript under `runs/<run-id>/`.
2. **score** — validates citations and runs the rubric judge per completion →
   `scores/<run-id>/scored.jsonl` + `score_summary.json`.
3. **stats** — bootstrap CIs + pairwise permutation tests →
   `stats/<run-id>/{stats.json,report.md}`.
4. **site** — renders the static leaderboard → `site/<run-id>/index.html`.

### The demo (what produces the leaderboard in this repo)

```bash
# 16 questions, 3 reps, all four slots:
auslex run --reps 3
#   → 3 commercial slots run as seeded mocks (no key configured)
#   → the "local" slot runs the REAL open-weight model via llama.cpp
```

The open-weight slot points at the local OpenAI-compatible server by default
(`http://localhost:10000/v1`, loaded model `14. Qwen3.8-27B (Q5_K_M)`). It is a
**real** inference run, not a mock.

### All commands

```bash
auslex author                          # regenerate the provisional sample set
auslex validate --questions data/questions/auslex.jsonl
                                       # schema + AU-jurisdiction + canary + dedup
auslex validate --questions ... --lock # + hash-lock the gold set + manifest
auslex probe-local --list              # is the local endpoint up? what's loaded?
auslex run [--models local,gpt] [--reps 3] [--no-score] [--no-stats]
auslex score runs/<run-id>             # re-score an existing run
auslex stats runs/<run-id>             # rebuild the stats report
auslex site runs/<run-id>              # publish the leaderboard site
auslex export-hf --out export/hf       # offline Hugging Face dataset export
auslex --help                          # full help
```

Useful flags on `run`:

- `--models local,gpt` — run only a subset of slots (comma-separated).
- `--reps N` — repeats per (model, question); default 3.
- `--out-root <dir>` / `--run-id <id>` — where the run lives.
- `--n-boot` / `--n-perm` — CI / permutation precision (default 10,000 each).

### Viewing the leaderboard

The site is a single self-contained `index.html` (inline CSS, no JS, no
external assets) built for GitHub Pages:

```bash
python3 -m http.server --directory site/<run-id> 8080
# open http://localhost:8080
```

To publish to GitHub Pages, point the Pages source at `site/<run-id>/` (or copy
its `index.html` to `docs/`).

---

## The four model slots

Config lives in `src/auslex/config.py` (a plain table). Resolution order:
**default < config file < environment**.

| Slot | Runner | Real when… | Mock fallback |
|---|---|---|---|
| `gpt` | OpenAI-compat | `OPENAI_API_KEY` set | seeded mock (quality 0.86, fab 0.08) |
| `claude` | Anthropic | `ANTHROPIC_API_KEY` set | seeded mock (quality 0.83, fab 0.10) |
| `gemini` | Google | `GOOGLE_API_KEY` set | seeded mock (quality 0.80, fab 0.13) |
| `local` | OpenAI-compat (local) | `base_url` reachable | seeded mock (quality 0.55, fab 0.25) |

Environment knobs for the local slot:

- `AUSLEX_LOCAL_BASE_URL` — default `http://localhost:10000/v1`
- `AUSLEX_LOCAL_MODEL` — default `14. Qwen3.8-27B (Q5_K_M)`
- `AUSLEX_LOCAL_ENABLE_THINKING` — **default `0` (off)**. See the note below.

Every completion records its `is_mock` flag end to end; mock rows are labelled
"synthetic" on the leaderboard and are **never** presented as real model
outputs. A mock runner is deterministic in `(slot, item_id, seed)`, so mock
runs are exactly reproducible.

> **Thinking models (the `local` slot).** The default open-weight model,
> Qwen3, is a *thinking* model: with chain-of-thought enabled it spends its
> whole `max_tokens` budget in `reasoning_content` and returns an **empty**
> answer. The harness therefore sends
> `chat_template_kwargs: {"enable_thinking": false}` by default so the model
> produces a normal answer. Non-Qwen OpenAI-compatible servers ignore unknown
> template kwargs, so this is safe. Set
> `AUSLEX_LOCAL_ENABLE_THINKING=1` to opt a local model back into thinking
> (you will then need a much larger `max_tokens`, and the empty-answer guard in
> `runners/local_runner.py` will explain the situation if you don't).

---

## Reproducibility & provenance

- **Append-only runs.** `runs/<run-id>/` holds `meta.json` (an immutable config
  snapshot: models, item content-hashes, seeds, prompt-template version,
  Python/platform versions, canary), an append-only `records.jsonl`, and the
  full raw provider payload per completion under `raw/<model>/<item>/rep_NN.json`.
  Nothing in a run dir is ever rewritten in place.
- **Content hashing.** Items are locked by content hash; run outputs are
  addressed by content hash, so the benchmark is tamper-evident.
- **Seeded statistics.** Bootstrap CIs and permutation p-values are fully
  reproducible for a given seed.
- **Single shared prompt.** Every model sees the identical, versioned prompt
  template — no per-model prompt tuning.

### Contamination control

Every item embeds the **global** canary (`auslex:9f2c1a4e-7b3d`) and a
**per-item** canary derived deterministically from its id. If an evaluated
model reproduces either verbatim, that is evidence the item was in its training
data. See `data/canary.txt` and
[`paper/CONTAMINATION_STATEMENT.md`](paper/CONTAMINATION_STATEMENT.md).

### The hard jurisdiction rule

An item's **gold answer** may rely only on Australian primary sources.
Comparative references (UK/US/NZ) are rejected at ingestion as a hard error
(`GOLD_NON_AU`); non-AU mentions in the question stem are a warning. This is a
*lint* (catches unambiguous non-AU report series and phrases), not a legal
oracle — it is deliberately conservative about Australian reporters.

---

## Web UI

A local web server provides a browser-based interface for configuring runs,
watching progress live, and exploring results.

```bash
# Start the server (default: http://localhost:8000)
pip install -e ".[ui]"
auslex-ui
```

The UI serves the static React+Vite app from `src/auslex/publish/assets/` and
proxies API requests to the Python harness. Endpoints:

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/health` | Liveness probe |
| `GET` | `/api/slots` | Slot roster + reachability |
| `GET` | `/api/questions` | Question list |
| `GET` | `/api/questions/{id}` | Question detail |
| `GET` | `/api/keys` | Read current key config (masked) |
| `PUT` | `/api/keys` | Write keys (stored locally, never transmitted externally) |
| `POST` | `/api/keys/test/{provider}` | Ping a provider to confirm the key works |
| `POST` | `/api/runs` | Launch a run |
| `GET` | `/api/runs/{id}/status` | Poll run progress (JSON) |
| `GET` | `/api/runs/{id}/stream` | SSE stream of run progress |
| `GET` | `/api/runs` | List past runs |
| `GET` | `/api/runs/{id}/report` | Stats report (leaderboard JSON) |
| `GET` | `/api/runs/{id}/item-results` | Per-item scores |
| `GET` | `/api/runs/{id}/records` | Full records as JSON |
| `GET` | `/api/local/probe` | Probe the local OpenAI-compatible endpoint |
| `POST` | `/api/runs/{id}/export-site` | Publish static leaderboard |
| `POST` | `/api/runs/{id}/export-hf` | Hugging Face dataset export |
| `GET` | `/api/runs/{id}/download` | Download run bundle |

API credentials are stored in `~/.auslex-ui/keys.json` (mode `0600`) and are
never sent to third-party services or logged. The UI runs entirely on your
machine — no telemetry, no external calls.

---

## Tests

```bash
python3 -m pytest
```

66 tests cover the canary layer, item schema, AU-jurisdiction filters,
citation extraction/classification, permutation test, config (including the
`enable_thinking` default-off + env override), content hashing, mock-runner
determinism, a mock-only end-to-end (run → score → stats), and the CLI.

Backend API tests (`tests/test_backend.py`) cover the FastAPI endpoints,
secrets store, and CLI entrypoint.

---

## Data & licensing

**Two-part license** (see [`LICENSE`](LICENSE)):

1. **Harness / code** (`src/`, `tests/`, `paper/`, packaging) — **Apache-2.0**.
2. **Question data** — **CC BY 4.0**.

The sample items are provisional exam-style drafts. They are realistic in form
but have **not** been checked by a qualified Australian lawyer, so gold
answers and the `required_authorities` may contain errors. Treat them as
placeholder scaffolding for the methodology, not as authoritative law.

---

## Disclaimer

This is a benchmarking **prototype**, not legal advice and not a source of
law. The shipped questions are unverified. Do not rely on any content here —
or on any model output it produces — for real legal decisions.

---

## Feedback

This is an early, deliberately narrow cut. The most valuable feedback right
now:

- **Legal accuracy** — if you are a qualified AU lawyer: are the provisional
  items' gold answers and required authorities plausible? What would a real
  question bank need to be lawyer-verifiable at scale?
- **Method** — is fabricated-citation-rate the right headline metric? Does the
  citation extractor handle the citation styles you care about?
- **Scope** — which question types / Priestley areas should be prioritized to
  reach the 100–200 target?

Please open issues on the repo or reach out directly. See
[`paper/ANALYSIS_PLAN.md`](paper/ANALYSIS_PLAN.md) for the planned analysis and
what the numbers will (and won't) mean at the current 16-item scale.
