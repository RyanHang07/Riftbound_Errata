# Recall run recall-as-of-2026-10-02T2251Z

vector, as_of filter before ranking; nomic-embed-text @ 0a109f422b47; corpus c295cdf13f95; questions 400c836ff4dc.
Hit = expected version-qualified ref, in effect on as_of (A1). Wilson 95% in brackets.

## recall@k (headline)

| stratum | @1 | @3 | @5 | @10 | @20 | unknown |
|---|---|---|---|---|---|---|
| expert-ruling | 51/160 = 32% [25%, 39%] | 84/160 = 52% [45%, 60%] | 93/160 = 58% [50%, 65%] | 116/160 = 72% [65%, 79%] | 128/160 = 80% [73%, 85%] | 0 |
| expert-ruling-faq | 3/8 = 38% [14%, 69%] | 5/8 = 62% [31%, 86%] | 5/8 = 62% [31%, 86%] | 7/8 = 88% [53%, 98%] | 8/8 = 100% [68%, 100%] | 0 |
| version-change | 21/56 = 38% [26%, 51%] | 30/56 = 54% [41%, 66%] | 33/56 = 59% [46%, 71%] | 36/56 = 64% [51%, 76%] | 47/56 = 84% [72%, 91%] | 0 |

## Secondary at k=5 (never the headline)

| stratum | recall@5 | version-blind recall@5 | wrong-version copy in top 5 | wrong-version copy ranked above the hit |
|---|---|---|---|---|
| expert-ruling | 93/160 = 58% [50%, 65%] | 93/160 = 58% [50%, 65%] | 0/160 = 0% [0%, 2%] | 0/160 = 0% [0%, 2%] |
| expert-ruling-faq | 5/8 = 62% [31%, 86%] | 5/8 = 62% [31%, 86%] | 0/8 = 0% [0%, 32%] | 0/8 = 0% [0%, 32%] |
| version-change | 33/56 = 59% [46%, 71%] | 33/56 = 59% [46%, 71%] | 0/56 = 0% [0%, 6%] | 0/56 = 0% [0%, 6%] |

## Prompt length at k=5 (for the A23 budget)

cl100k tokens over 224 prompts: median 988, p90 1513, max 1879. cl100k is not the generator's tokenizer; Ollama's own counts come with slice 6.
