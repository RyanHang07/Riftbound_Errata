# Answers answers-qwen3-2026-11-03T0511Z

qwen3:4b-instruct-2507-q4_K_M @ 0edcdef34593; think False, temperature 0.0, seed 42, num_ctx 8192, max 400 tokens; template 77ae5735af41; retrieval as-of k=5; placement: 100% on GPU.

## Generation

224 answers. Seconds per answer (prefill + decode, Ollama's clock): median 1.91, p90 3.60. Answer tokens: median 148.
Ollama connections dropped and retried: 2. Stopped at the token cap: 11. Answers with copied rule text removed: 99.

## Judged by qwen3:4b-instruct-2507-q4_K_M @ 0edcdef34593

Usable only if the kappa below says so. Accuracy given a hit is the headline; unconditioned is shown beside it, never instead.

| stratum | accuracy given a hit (top 5) | unconditioned | not answered | unparsed |
|---|---|---|---|---|
| expert-ruling | 54/100 = 54% [44%, 63%] | 64/160 = 40% [33%, 48%] | 3 | 0 |
| expert-ruling-faq | 0/3 = 0% [0%, 56%] | 0/8 = 0% [0%, 32%] | 0 | 0 |
| version-change | 29/45 = 64% [50%, 77%] | 37/56 = 66% [53%, 77%] | 0 | 0 |

### Judge against hand labels (60 answers)

- correct vs not: kappa 0.77 [0.59, 0.90] (substantial)
- three verdicts: kappa 0.43 [0.31, 0.56] (moderate)
- "correct" rate on these answers: hand 53%, judge 55%

| hand \ judge | correct | incorrect | not_answered |
|---|---|---|---|
| correct | 29 | 3 | 0 |
| incorrect | 0 | 9 | 0 |
| not_answered | 4 | 15 | 0 |

