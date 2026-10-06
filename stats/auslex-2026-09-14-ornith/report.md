# AusLawExam-Bench run report

Run `auslex-2026-09-14-ornith`, 1 models, 12 questions.

## Leaderboard (item score 0 to 100, with 95% CI)

| Model | Mean score (95% CI) | Fabricated-citation rate (95% CI) | Questions |
|---|---|---|---|
| local | 70.3 [59.4, 80.5] | 0.906 [0.817, 0.976] | 12 |

## Pairwise significance (paired permutation, two-sided)

| Model A | Model B | Mean diff (A - B) | p-value | Significant at 0.05 |
|---|---|---|---|---|

*Method: percentile bootstrap, n_boot=10000, resampling questions; the fabricated rate is the pooled ratio, recomputed on each resample; paired permutation (sign-flip), n_perm=10000, two-sided, seeded.*
