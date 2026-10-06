# AusLawExam-Bench run report

Run `auslex-2026-10-06-claude`, 1 models, 16 questions.

## Leaderboard (item score 0 to 100, with 95% CI)

| Model | Mean score (95% CI) | Fabricated-citation rate (95% CI) | Questions |
|---|---|---|---|
| claude | 89.3 [85.7, 92.6] | 0.889 [0.847, 0.929] | 16 |

## Pairwise significance (paired permutation, two-sided)

| Model A | Model B | Mean diff (A - B) | p-value | Significant at 0.05 |
|---|---|---|---|---|

*Method: percentile bootstrap, n_boot=10000, resampling questions; the fabricated rate is the pooled ratio, recomputed on each resample; paired permutation (sign-flip), n_perm=10000, two-sided, seeded.*
