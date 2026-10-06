# Recall run recall-rerank-qwen3-2026-10-04T1446Z

cross-encoder over vector top N + full-text top N, as_of filter; qwen3-embedding:0.6b @ ac6da0dfba84; corpus c295cdf13f95; questions 400c836ff4dc.
Hit = expected version-qualified ref, in effect on as_of (A1). Wilson 95% in brackets.

## recall@k (headline)

| stratum | @1 | @3 | @5 | @10 | @20 | unknown |
|---|---|---|---|---|---|---|
| expert-ruling | 52/160 = 32% [26%, 40%] | 95/160 = 59% [52%, 67%] | 105/160 = 66% [58%, 73%] | 123/160 = 77% [70%, 83%] | 141/160 = 88% [82%, 92%] | 0 |
| expert-ruling-faq | 1/8 = 12% [2%, 47%] | 3/8 = 38% [14%, 69%] | 3/8 = 38% [14%, 69%] | 6/8 = 75% [41%, 93%] | 6/8 = 75% [41%, 93%] | 0 |
| version-change | 30/56 = 54% [41%, 66%] | 42/56 = 75% [62%, 84%] | 49/56 = 88% [76%, 94%] | 52/56 = 93% [83%, 97%] | 54/56 = 96% [88%, 99%] | 0 |

## Secondary at k=5 (never the headline)

| stratum | recall@5 | version-blind recall@5 | wrong-version copy in top 5 | wrong-version copy ranked above the hit |
|---|---|---|---|---|
| expert-ruling | 105/160 = 66% [58%, 73%] | 105/160 = 66% [58%, 73%] | 0/160 = 0% [0%, 2%] | 0/160 = 0% [0%, 2%] |
| expert-ruling-faq | 3/8 = 38% [14%, 69%] | 3/8 = 38% [14%, 69%] | 0/8 = 0% [0%, 32%] | 0/8 = 0% [0%, 32%] |
| version-change | 49/56 = 88% [76%, 94%] | 49/56 = 88% [76%, 94%] | 0/56 = 0% [0%, 6%] | 0/56 = 0% [0%, 6%] |

## recall@5 by group

| group | recall@5 |
|---|---|
| expert-ruling | 105/160 = 66% [58%, 73%] |
| expert-ruling-faq | 3/8 = 38% [14%, 69%] |
| version-change | 49/56 = 88% [76%, 94%] |
|   ruling: cards | 66/113 = 58% [49%, 67%] |
|   ruling: general-rules | 19/26 = 73% [54%, 86%] |
|   ruling: mechanics | 20/21 = 95% [77%, 99%] |

## Retrieval latency per question (embedding + SQL + rerank)

median 10513 ms, p90 11932 ms, max 13310 ms over 224 questions. The first question includes model loading.

## Prompt length at k=5 (for the A23 budget)

cl100k tokens over 224 prompts: median 1103, p90 1648, max 2069. cl100k is not the generator's tokenizer; Ollama's own counts come with generation (slice 11).
