# Recall run recall-as-of-qwen3-2026-10-04T1415Z

vector, as_of filter before ranking; qwen3-embedding:0.6b @ ac6da0dfba84; corpus c295cdf13f95; questions 400c836ff4dc.
Hit = expected version-qualified ref, in effect on as_of (A1). Wilson 95% in brackets.

## recall@k (headline)

| stratum | @1 | @3 | @5 | @10 | @20 | unknown |
|---|---|---|---|---|---|---|
| expert-ruling | 62/160 = 39% [32%, 46%] | 84/160 = 52% [45%, 60%] | 100/160 = 62% [55%, 70%] | 121/160 = 76% [68%, 82%] | 137/160 = 86% [79%, 90%] | 0 |
| expert-ruling-faq | 2/8 = 25% [7%, 59%] | 2/8 = 25% [7%, 59%] | 3/8 = 38% [14%, 69%] | 5/8 = 62% [31%, 86%] | 6/8 = 75% [41%, 93%] | 0 |
| version-change | 29/56 = 52% [39%, 64%] | 41/56 = 73% [60%, 83%] | 44/56 = 79% [66%, 87%] | 48/56 = 86% [74%, 93%] | 52/56 = 93% [83%, 97%] | 0 |

## Secondary at k=5 (never the headline)

| stratum | recall@5 | version-blind recall@5 | wrong-version copy in top 5 | wrong-version copy ranked above the hit |
|---|---|---|---|---|
| expert-ruling | 100/160 = 62% [55%, 70%] | 100/160 = 62% [55%, 70%] | 0/160 = 0% [0%, 2%] | 0/160 = 0% [0%, 2%] |
| expert-ruling-faq | 3/8 = 38% [14%, 69%] | 3/8 = 38% [14%, 69%] | 0/8 = 0% [0%, 32%] | 0/8 = 0% [0%, 32%] |
| version-change | 44/56 = 79% [66%, 87%] | 44/56 = 79% [66%, 87%] | 0/56 = 0% [0%, 6%] | 0/56 = 0% [0%, 6%] |

## recall@5 by group

| group | recall@5 |
|---|---|
| expert-ruling | 100/160 = 62% [55%, 70%] |
| expert-ruling-faq | 3/8 = 38% [14%, 69%] |
| version-change | 44/56 = 79% [66%, 87%] |
|   ruling: cards | 62/113 = 55% [46%, 64%] |
|   ruling: general-rules | 19/26 = 73% [54%, 86%] |
|   ruling: mechanics | 19/21 = 90% [71%, 97%] |

## Prompt length at k=5 (for the A23 budget)

cl100k tokens over 224 prompts: median 825, p90 1427, max 1771. cl100k is not the generator's tokenizer; Ollama's own counts come with generation (slice 11).
