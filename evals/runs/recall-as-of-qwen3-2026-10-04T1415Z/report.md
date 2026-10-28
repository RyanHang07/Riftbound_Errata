# Recall run recall-as-of-qwen3-2026-10-04T1415Z

vector, as_of filter before ranking; qwen3-embedding:0.6b @ ac6da0dfba84; corpus c295cdf13f95; questions 400c836ff4dc.
Hit = expected version-qualified ref, in effect on as_of (A1). Wilson 95% in brackets.

Labels changed since this run: 2 of its questions are no longer in the set (v-countered-spell-played-v1.3, v-legion-countered-spell-v1.3) and 2 questions in the set were not run (v-countered-spell-played-v1.2, v-legion-countered-spell-v1.2). Graded on the questions both share; rerun to include the rest.

## recall@k (headline)

| stratum | @1 | @3 | @5 | @10 | @20 | unknown |
|---|---|---|---|---|---|---|
| expert-ruling | 62/160 = 39% [32%, 46%] | 84/160 = 52% [45%, 60%] | 100/160 = 62% [55%, 70%] | 121/160 = 76% [68%, 82%] | 137/160 = 86% [79%, 90%] | 0 |
| expert-ruling-faq | 2/8 = 25% [7%, 59%] | 2/8 = 25% [7%, 59%] | 3/8 = 38% [14%, 69%] | 5/8 = 62% [31%, 86%] | 6/8 = 75% [41%, 93%] | 0 |
| version-change | 28/54 = 52% [39%, 65%] | 40/54 = 74% [61%, 84%] | 43/54 = 80% [67%, 88%] | 46/54 = 85% [73%, 92%] | 50/54 = 93% [82%, 97%] | 0 |

## Secondary at k=5 (never the headline)

| stratum | recall@5 | version-blind recall@5 | wrong-version copy in top 5 | wrong-version copy ranked above the hit |
|---|---|---|---|---|
| expert-ruling | 100/160 = 62% [55%, 70%] | 100/160 = 62% [55%, 70%] | 0/160 = 0% [0%, 2%] | 0/160 = 0% [0%, 2%] |
| expert-ruling-faq | 3/8 = 38% [14%, 69%] | 3/8 = 38% [14%, 69%] | 0/8 = 0% [0%, 32%] | 0/8 = 0% [0%, 32%] |
| version-change | 43/54 = 80% [67%, 88%] | 43/54 = 80% [67%, 88%] | 0/54 = 0% [0%, 7%] | 0/54 = 0% [0%, 7%] |

## recall@5 by group

| group | recall@5 |
|---|---|
| expert-ruling | 100/160 = 62% [55%, 70%] |
| expert-ruling-faq | 3/8 = 38% [14%, 69%] |
| version-change | 43/54 = 80% [67%, 88%] |
|   ruling: cards | 62/113 = 55% [46%, 64%] |
|   ruling: general-rules | 19/26 = 73% [54%, 86%] |
|   ruling: mechanics | 19/21 = 90% [71%, 97%] |

## Prompt length at k=5 (for the A23 budget)

cl100k tokens over 222 prompts: median 829, p90 1427, max 1771. cl100k is not the generator's tokenizer; Ollama's own counts come with generation (slice 11).
