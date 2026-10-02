# Recall run recall-2026-10-02T2236Z

naive-vector, no date filter; nomic-embed-text @ 0a109f422b47; corpus c295cdf13f95; questions 400c836ff4dc.
Hit = expected version-qualified ref, in effect on as_of (A1). Wilson 95% in brackets.

## recall@k (headline)

| stratum | @1 | @3 | @5 | @10 | @20 | unknown |
|---|---|---|---|---|---|---|
| expert-ruling | 30/160 = 19% [13%, 26%] | 55/160 = 34% [27%, 42%] | 70/160 = 44% [36%, 51%] | 83/160 = 52% [44%, 59%] | 101/160 = 63% [55%, 70%] | 0 |
| expert-ruling-faq | 1/8 = 12% [2%, 47%] | 4/8 = 50% [22%, 78%] | 5/8 = 62% [31%, 86%] | 5/8 = 62% [31%, 86%] | 6/8 = 75% [41%, 93%] | 0 |
| version-change | 6/56 = 11% [5%, 21%] | 15/56 = 27% [17%, 40%] | 22/56 = 39% [28%, 52%] | 30/56 = 54% [41%, 66%] | 33/56 = 59% [46%, 71%] | 0 |

## Secondary at k=5 (never the headline)

| stratum | recall@5 | version-blind recall@5 | wrong-version copy in top 5 | wrong-version copy ranked above the hit |
|---|---|---|---|---|
| expert-ruling | 70/160 = 44% [36%, 51%] | 75/160 = 47% [39%, 55%] | 25/160 = 16% [11%, 22%] | 9/160 = 6% [3%, 10%] |
| expert-ruling-faq | 5/8 = 62% [31%, 86%] | 5/8 = 62% [31%, 86%] | 0/8 = 0% [0%, 32%] | 0/8 = 0% [0%, 32%] |
| version-change | 22/56 = 39% [28%, 52%] | 29/56 = 52% [39%, 64%] | 25/56 = 45% [32%, 58%] | 16/56 = 29% [18%, 41%] |

## Prompt length at k=5 (for the A23 budget)

cl100k tokens over 224 prompts: median 846, p90 1629, max 2070. cl100k is not the generator's tokenizer; Ollama's own counts come with slice 6.
