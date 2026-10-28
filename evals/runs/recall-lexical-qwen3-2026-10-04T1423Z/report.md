# Recall run recall-lexical-qwen3-2026-10-04T1423Z

postgres full-text (stemmed terms ORed), as_of filter; qwen3-embedding:0.6b @ ac6da0dfba84; corpus c295cdf13f95; questions 400c836ff4dc.
Hit = expected version-qualified ref, in effect on as_of (A1). Wilson 95% in brackets.

Labels changed since this run: 2 of its questions are no longer in the set (v-countered-spell-played-v1.3, v-legion-countered-spell-v1.3) and 2 questions in the set were not run (v-countered-spell-played-v1.2, v-legion-countered-spell-v1.2). Graded on the questions both share; rerun to include the rest.

## recall@k (headline)

| stratum | @1 | @3 | @5 | @10 | @20 | unknown |
|---|---|---|---|---|---|---|
| expert-ruling | 42/160 = 26% [20%, 34%] | 70/160 = 44% [36%, 51%] | 85/160 = 53% [45%, 61%] | 114/160 = 71% [64%, 78%] | 125/160 = 78% [71%, 84%] | 0 |
| expert-ruling-faq | 2/8 = 25% [7%, 59%] | 3/8 = 38% [14%, 69%] | 3/8 = 38% [14%, 69%] | 4/8 = 50% [22%, 78%] | 5/8 = 62% [31%, 86%] | 0 |
| version-change | 7/54 = 13% [6%, 24%] | 14/54 = 26% [16%, 39%] | 19/54 = 35% [24%, 49%] | 31/54 = 57% [44%, 70%] | 38/54 = 70% [57%, 81%] | 0 |

## Secondary at k=5 (never the headline)

| stratum | recall@5 | version-blind recall@5 | wrong-version copy in top 5 | wrong-version copy ranked above the hit |
|---|---|---|---|---|
| expert-ruling | 85/160 = 53% [45%, 61%] | 85/160 = 53% [45%, 61%] | 0/160 = 0% [0%, 2%] | 0/160 = 0% [0%, 2%] |
| expert-ruling-faq | 3/8 = 38% [14%, 69%] | 3/8 = 38% [14%, 69%] | 0/8 = 0% [0%, 32%] | 0/8 = 0% [0%, 32%] |
| version-change | 19/54 = 35% [24%, 49%] | 19/54 = 35% [24%, 49%] | 0/54 = 0% [0%, 7%] | 0/54 = 0% [0%, 7%] |

## recall@5 by group

| group | recall@5 |
|---|---|
| expert-ruling | 85/160 = 53% [45%, 61%] |
| expert-ruling-faq | 3/8 = 38% [14%, 69%] |
| version-change | 19/54 = 35% [24%, 49%] |
|   ruling: cards | 55/113 = 49% [40%, 58%] |
|   ruling: general-rules | 16/26 = 62% [43%, 78%] |
|   ruling: mechanics | 14/21 = 67% [45%, 83%] |

## Prompt length at k=5 (for the A23 budget)

cl100k tokens over 222 prompts: median 1792, p90 2015, max 2174. cl100k is not the generator's tokenizer; Ollama's own counts come with generation (slice 11).
