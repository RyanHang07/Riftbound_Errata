# Recall run recall-hybrid-qwen3-2026-10-04T1423Z

RRF(vector, full-text) k=60 over top 50 each, as_of filter; qwen3-embedding:0.6b @ ac6da0dfba84; corpus c295cdf13f95; questions 400c836ff4dc.
Hit = expected version-qualified ref, in effect on as_of (A1). Wilson 95% in brackets.

## recall@k (headline)

| stratum | @1 | @3 | @5 | @10 | @20 | unknown |
|---|---|---|---|---|---|---|
| expert-ruling | 70/160 = 44% [36%, 51%] | 93/160 = 58% [50%, 65%] | 106/160 = 66% [59%, 73%] | 121/160 = 76% [68%, 82%] | 137/160 = 86% [79%, 90%] | 0 |
| expert-ruling-faq | 1/8 = 12% [2%, 47%] | 5/8 = 62% [31%, 86%] | 5/8 = 62% [31%, 86%] | 5/8 = 62% [31%, 86%] | 5/8 = 62% [31%, 86%] | 0 |
| version-change | 17/56 = 30% [20%, 43%] | 32/56 = 57% [44%, 69%] | 37/56 = 66% [53%, 77%] | 47/56 = 84% [72%, 91%] | 49/56 = 88% [76%, 94%] | 0 |

## Secondary at k=5 (never the headline)

| stratum | recall@5 | version-blind recall@5 | wrong-version copy in top 5 | wrong-version copy ranked above the hit |
|---|---|---|---|---|
| expert-ruling | 106/160 = 66% [59%, 73%] | 106/160 = 66% [59%, 73%] | 0/160 = 0% [0%, 2%] | 0/160 = 0% [0%, 2%] |
| expert-ruling-faq | 5/8 = 62% [31%, 86%] | 5/8 = 62% [31%, 86%] | 0/8 = 0% [0%, 32%] | 0/8 = 0% [0%, 32%] |
| version-change | 37/56 = 66% [53%, 77%] | 37/56 = 66% [53%, 77%] | 0/56 = 0% [0%, 6%] | 0/56 = 0% [0%, 6%] |

## recall@5 by group

| group | recall@5 |
|---|---|
| expert-ruling | 106/160 = 66% [59%, 73%] |
| expert-ruling-faq | 5/8 = 62% [31%, 86%] |
| version-change | 37/56 = 66% [53%, 77%] |
|   ruling: cards | 68/113 = 60% [51%, 69%] |
|   ruling: general-rules | 20/26 = 77% [58%, 89%] |
|   ruling: mechanics | 18/21 = 86% [65%, 95%] |

## Prompt length at k=5 (for the A23 budget)

cl100k tokens over 224 prompts: median 1362, p90 1920, max 2081. cl100k is not the generator's tokenizer; Ollama's own counts come with generation (slice 11).
