# Confidence for answers-qwen3-2026-11-03T0511Z

Labels: judgments-qwen3-4b-instruct-2507-q4-k-m.json (224 answers, 45% correct). Out-of-fold probabilities, 5 folds, seed 20261103. Usable only if that judge's kappa is.

**Calibrated.** ECE 0.068 (pass: at most 0.1); Brier 0.190 against 0.248 for always predicting the base rate (skill +0.23).

| bin (low to high) | answers | mean confidence | observed correct |
|---|---|---|---|
| 1 | 45 | 1% | 0% |
| 2 | 45 | 33% | 51% |
| 3 | 45 | 54% | 51% |
| 4 | 45 | 65% | 60% |
| 5 | 44 | 71% | 64% |

Top bin minus bottom bin, observed: +64%.

## Signal weights (model fitted on all answers; standardised, so comparable)

| signal | weight | positive in |
|---|---|---|
| top_distance | -0.10 | continuous |
| margin | +0.06 | continuous |
| top_in_effect | +0.00 | constant: no signal |
| versions_disagree | +0.00 | constant: no signal |
| cites_any | +0.95 | 172 of 224 |
| cites_only_retrieved | +0.34 | 149 of 224 |
| cites_only_in_effect | +0.95 | 172 of 224 |
| abstains | -0.32 | 80 of 224 |
| log_answer_tokens | -0.09 | continuous |
