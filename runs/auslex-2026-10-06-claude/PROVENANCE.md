# Provenance: run auslex-2026-10-06-claude

This folder holds one run of the Claude slot against the live Anthropic API.  The files in it, and in the matching folders under `scores/`, `stats/`, and `site/`, are the unedited output of that run.

| Item | Value |
|---|---|
| Command | `auslex run --models claude --reps 3 --seed 0 --run-id auslex-2026-10-06-claude` |
| Run at | 2026-10-06, 12:09:31 to 12:26:02 UTC |
| Code revision | `462134f`, "Merge pull request #2 from Danielkgr/verify-authorities-and-api-runners", in a fresh clone |
| Questions | `data/questions/auslex.jsonl`, 16 provisional items, each pinned by the content hash in `meta.json` |
| Prompt | Shared template v1.0.0, the same system prompt for every slot |
| Model | `claude-opus-5-5` through `AnthropicRunner`, `high` effort, `max_tokens` of 32,000, the model's default temperature |
| Fallbacks | Off.  Every completion was answered by `claude-opus-5-5`. |
| Repetitions | 3 per item, seed 0, for 48 completions |
| Python | 3.14.4 |

| Outcome | Value |
|---|---|
| Completions | 48 finished with `end_turn`, 0 errors, 0 retries |
| Output tokens per completion | Median 8,826, lowest 2,386, highest 17,433, thinking included.  None reached the 32,000 limit. |
| Latency per completion | Median 88 seconds |
| Input tokens | 21,429 in total |
| Output tokens | 379,220 in total |
| Cost | $7.67, summed from each record's `cost_usd`, which is priced from the API's usage figures at list prices.  The invoice is the authority. |

The cost estimate before the run, from `auslex estimate --models claude --reps 3`, was $1.54, with a ceiling of $30.78 if every answer used its full budget.  The estimate leaves out thinking tokens and assumes the local run's answer length, and Claude's visible answers alone ran to about 2,500 tokens each.

## Scoring

`auslex run` scored the completions, computed the intervals, and rendered the leaderboard in the same command, with the shipped scorer and judge and no change to either.

- The rubric judge is the deterministic seeded mock ensemble.  It derives a quality signal from how many of the item's required authorities an answer names, how many words of its key issues it uses, whether it states a conclusion, and its length, then adds small seeded noise per judge.  The mean item score of 89.3 measures that signal, not legal quality.
- The citation checker classed 47 citations `on_point`, 47 `known_other`, and 753 `fabricated`, of 847.  `fabricated` means the matcher could not confirm the citation against the item's required authorities or the 48-entry known corpus.  The most frequent members of that class are real and well-known authorities, so the rate of 0.889 is an upper bound.  No citation has yet had a legal check.
- One extraction fault is visible in the output.  The extractor cuts *Pavey & Matthews Pty Ltd v Paul* (1987) 162 CLR 221 at the ampersand and records it as `Matthews Pty Ltd v Paul`, all 7 times it appears.

This was the first and only run of the Claude slot.  No question, prompt, scorer, or judge was changed after it.

## Reproducing it

Check out revision `462134f`, install with `pip install -e ".[claude]"`, set `ANTHROPIC_API_KEY`, and run the command above with a new run id.  Claude's answers will differ between runs, so the scores will too.  Re-scoring this run's committed raw outputs with `auslex score`, `auslex stats`, and `auslex site` on this folder needs no API key.  Re-running `auslex score` on 7 October 2026 reproduced `scored.jsonl` and `score_summary.json` byte for byte.
