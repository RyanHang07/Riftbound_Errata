# Recall run recall-rerank-vector-qwen3-2026-10-06T0459Z

cross-encoder over vector top 2N, as_of filter; qwen3-embedding:0.6b @ ac6da0dfba84; corpus c295cdf13f95; questions 400c836ff4dc.
Hit = expected version-qualified ref, in effect on as_of (A1). Wilson 95% in brackets.

## recall@k (headline)

| stratum | @1 | @3 | @5 | @10 | @20 | unknown |
|---|---|---|---|---|---|---|
| expert-ruling | 54/160 = 34% [27%, 41%] | 94/160 = 59% [51%, 66%] | 107/160 = 67% [59%, 74%] | 125/160 = 78% [71%, 84%] | 139/160 = 87% [81%, 91%] | 0 |
| expert-ruling-faq | 1/8 = 12% [2%, 47%] | 3/8 = 38% [14%, 69%] | 3/8 = 38% [14%, 69%] | 6/8 = 75% [41%, 93%] | 6/8 = 75% [41%, 93%] | 0 |
| version-change | 29/56 = 52% [39%, 64%] | 43/56 = 77% [64%, 86%] | 48/56 = 86% [74%, 93%] | 54/56 = 96% [88%, 99%] | 56/56 = 100% [94%, 100%] | 0 |

## Secondary at k=5 (never the headline)

| stratum | recall@5 | version-blind recall@5 | wrong-version copy in top 5 | wrong-version copy ranked above the hit |
|---|---|---|---|---|
| expert-ruling | 107/160 = 67% [59%, 74%] | 107/160 = 67% [59%, 74%] | 0/160 = 0% [0%, 2%] | 0/160 = 0% [0%, 2%] |
| expert-ruling-faq | 3/8 = 38% [14%, 69%] | 3/8 = 38% [14%, 69%] | 0/8 = 0% [0%, 32%] | 0/8 = 0% [0%, 32%] |
| version-change | 48/56 = 86% [74%, 93%] | 48/56 = 86% [74%, 93%] | 0/56 = 0% [0%, 6%] | 0/56 = 0% [0%, 6%] |

## recall@5 by group

| group | recall@5 |
|---|---|
| expert-ruling | 107/160 = 67% [59%, 74%] |
| expert-ruling-faq | 3/8 = 38% [14%, 69%] |
| version-change | 48/56 = 86% [74%, 93%] |
|   ruling: cards | 67/113 = 59% [50%, 68%] |
|   ruling: general-rules | 20/26 = 77% [58%, 89%] |
|   ruling: mechanics | 20/21 = 95% [77%, 99%] |

## Retrieval latency per question (embedding + SQL + rerank)

median 12459 ms, p90 14198 ms, max 20534 ms over 224 questions. The first question includes model loading.

## Prompt length at k=5 (for the A23 budget)

cl100k tokens over 224 prompts: median 984, p90 1551, max 2006. cl100k is not the generator's tokenizer; Ollama's own counts come with generation (slice 11).
