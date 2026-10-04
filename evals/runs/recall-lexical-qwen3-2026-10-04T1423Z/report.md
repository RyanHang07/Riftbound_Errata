# Recall run recall-lexical-qwen3-2026-10-04T1423Z

postgres full-text (stemmed terms ORed), as_of filter; qwen3-embedding:0.6b @ ac6da0dfba84; corpus c295cdf13f95; questions 400c836ff4dc.
Hit = expected version-qualified ref, in effect on as_of (A1). Wilson 95% in brackets.

## recall@k (headline)

| stratum | @1 | @3 | @5 | @10 | @20 | unknown |
|---|---|---|---|---|---|---|
| expert-ruling | 42/160 = 26% [20%, 34%] | 70/160 = 44% [36%, 51%] | 85/160 = 53% [45%, 61%] | 114/160 = 71% [64%, 78%] | 125/160 = 78% [71%, 84%] | 0 |
| expert-ruling-faq | 2/8 = 25% [7%, 59%] | 3/8 = 38% [14%, 69%] | 3/8 = 38% [14%, 69%] | 4/8 = 50% [22%, 78%] | 5/8 = 62% [31%, 86%] | 0 |
| version-change | 7/56 = 12% [6%, 24%] | 14/56 = 25% [16%, 38%] | 19/56 = 34% [23%, 47%] | 32/56 = 57% [44%, 69%] | 40/56 = 71% [59%, 82%] | 0 |

## Secondary at k=5 (never the headline)

| stratum | recall@5 | version-blind recall@5 | wrong-version copy in top 5 | wrong-version copy ranked above the hit |
|---|---|---|---|---|
| expert-ruling | 85/160 = 53% [45%, 61%] | 85/160 = 53% [45%, 61%] | 0/160 = 0% [0%, 2%] | 0/160 = 0% [0%, 2%] |
| expert-ruling-faq | 3/8 = 38% [14%, 69%] | 3/8 = 38% [14%, 69%] | 0/8 = 0% [0%, 32%] | 0/8 = 0% [0%, 32%] |
| version-change | 19/56 = 34% [23%, 47%] | 19/56 = 34% [23%, 47%] | 0/56 = 0% [0%, 6%] | 0/56 = 0% [0%, 6%] |

## recall@5 by group

| group | recall@5 |
|---|---|
| expert-ruling | 85/160 = 53% [45%, 61%] |
| expert-ruling-faq | 3/8 = 38% [14%, 69%] |
| version-change | 19/56 = 34% [23%, 47%] |
|   ruling: cards | 55/113 = 49% [40%, 58%] |
|   ruling: general-rules | 16/26 = 62% [43%, 78%] |
|   ruling: mechanics | 14/21 = 67% [45%, 83%] |

## Prompt length at k=5 (for the A23 budget)

cl100k tokens over 224 prompts: median 1789, p90 2015, max 2174. cl100k is not the generator's tokenizer; Ollama's own counts come with generation (slice 11).
