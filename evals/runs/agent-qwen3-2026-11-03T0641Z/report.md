# Answers agent-qwen3-2026-11-03T0641Z

qwen3:4b-instruct-2507-q4_K_M @ 0edcdef34593; think False, temperature 0.0, seed 42, num_ctx 8192, max 400 tokens; template 77ae5735af41; retrieval as-of k=5; placement: 100% on GPU.

## Generation

224 answers. Seconds per answer (prefill + decode, Ollama's clock): median 3.35, p90 7.88. Answer tokens: median 164.
Ollama connections dropped and retried: 8. Stopped at the token cap: 0. Answers with copied rule text removed: 106.

## Judged by qwen3:4b-instruct-2507-q4_K_M @ 0edcdef34593

Usable only if the kappa below says so. Accuracy given a hit is the headline; unconditioned is shown beside it, never instead.

| stratum | accuracy given a hit (top 5) | unconditioned | not answered | unparsed |
|---|---|---|---|---|
| expert-ruling | 58/100 = 58% [48%, 67%] | 73/160 = 46% [38%, 53%] | 2 | 0 |
| expert-ruling-faq | 1/3 = 33% [6%, 79%] | 2/8 = 25% [7%, 59%] | 0 | 0 |
| version-change | 31/45 = 69% [54%, 80%] | 37/56 = 66% [53%, 77%] | 0 | 0 |

No kappa here: the hand labels grade answers-qwen3-2026-11-03T0511Z's answers, not this run's. This judge's validity rests on that run's kappa.

