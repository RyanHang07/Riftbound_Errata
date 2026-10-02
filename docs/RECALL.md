# Slice 5: recall@k baseline

Naive vector retrieval (no date filter), every question in
`evals/questions.yaml`, top 20 kept. Run with `make recall`; recompute any
committed run offline with `make recall-report RUN=evals/runs/recall-...`.

## Prediction (written 2026-10-02, before the first real run)

Brief section 2: predicting afterwards is how a null result becomes a success
story. These are written before any real number exists. The basis is slice 3,
where the answering rule was missing from the top 5 for 4 of 10 candidates
and an outdated rule was ranked first for 3 of 10.

| Stratum | Metric | Prediction | Why |
|---|---|---|---|
| expert-ruling | recall@5 | about 25%, plausible 15 to 40% | Questions name cards ("Does Abandoned Hall trigger..."), and the corpus has no card text. The embedder has to bridge from a card name to rule language. |
| expert-ruling | recall@20 | about 45% | Same gap, more room. |
| version-change | recall@5 | about 55%, plausible 40 to 70% | Written from the diff in rule language; slice 3 found the rule in 6 of 10. |
| expert-ruling-faq | any | no prediction | n = 8 gives a Wilson interval about 60 points wide. Reported, not interpreted. |
| version-change | wrong-version copy in top 5 | at least 30% | Versions of a rule are near-duplicates, so they sit next to each other in embedding space. |
| version-change | wrong-version copy ranked above the hit | 15 to 25% | Slice 3: 3 of 10. |
| version-change | version-blind minus recall@5 | at least 5 points | The gap A1 exists to make visible. |

If expert-ruling recall@5 comes in above 40%, the card-name gap is smaller
than assumed and slice 8 (hybrid search) has less to win. If version-change
recall@5 is below 40%, slice 3's ten candidates were easier than the set.

## Definitions

- **Hit:** a retrieved chunk carries an expected version-qualified ref and is
  in effect on the question's as_of (A1, A16). Any one expected ref is
  enough.
- **Unknown:** the search errored. Never counted as a miss.
- **Wrong-version copy:** the same rule found in another version by text
  alignment (`evals/counterparts.json`, never by number: A15), whose text
  differs and which is not in effect on as_of.
- **Version-blind recall:** the brief's original definition, any version.

## Results: first run `evals/runs/recall-2026-10-02T2236Z`

Run on the user's PC; embedder nomic-embed-text @ 0a109f422b47, corpus
c295cdf13f95. Recomputed offline from the committed snapshot in the cloud
session: identical report. The snapshot holds refs, dates and hashes only.
No question errored (unknown = 0 in every stratum).

| Stratum | @1 | @3 | @5 | @10 | @20 |
|---|---|---|---|---|---|
| expert-ruling (160) | 19% [13, 26] | 34% [27, 42] | **44% [36, 51]** | 52% [44, 59] | 63% [55, 70] |
| expert-ruling-faq (8) | 12% [2, 47] | 50% [22, 78] | 62% [31, 86] | 62% [31, 86] | 75% [41, 93] |
| version-change (56) | 11% [5, 21] | 27% [17, 40] | **39% [28, 52]** | 54% [41, 66] | 59% [46, 71] |

Secondary, k = 5:

| Stratum | recall@5 | version-blind | wrong-version copy in top 5 | ranked above the hit |
|---|---|---|---|---|
| expert-ruling | 44% | 47% | 16% [11, 22] | 6% [3, 10] |
| expert-ruling-faq | 62% | 62% | 0% | 0% |
| version-change | 39% | 52% | 45% [32, 58] | **29% [18, 41]** |

### Against the prediction

| Prediction | Result | Verdict |
|---|---|---|
| expert-ruling recall@5 about 25% (15 to 40) | 44% [36, 51] | **Wrong, too low.** Interval clears 40%. |
| expert-ruling recall@20 about 45% | 63% [55, 70] | Wrong, too low. |
| version-change recall@5 about 55% (40 to 70) | 39% [28, 52] | **Wrong, too high**, at the bottom edge. |
| wrong-version copy in top 5 at least 30% | 45% [32, 58] | Right. |
| wrong-version copy above the hit 15 to 25% | 29% [18, 41] | Slightly above the range; interval overlaps it. |
| version-blind minus recall@5 at least 5 points | 13 points (29 vs 22 of 56) | Right. |

**What the two misses mean, by the rules written before the run:**

1. **The card-name gap is smaller than assumed.** Expert-ruling recall@5 is
   above 40%, so a question naming a card still lands near the right rule
   44% of the time. Slice 8 (hybrid search) has less to win on these than
   expected; its prediction must start from 44%, not 25%.
2. **Slice 3's ten candidates were easier than the set.** Version-change
   recall@5 is 39%, below the 40% threshold. Those ten were picked by reading
   the diff, and picking by hand favoured clear-cut rules.

**The finding slice 10 exists for.** On version-change questions, a
wrong-version copy of the expected rule is ranked above the right one in 16
of 56 (29%), and 7 of 56 find the rule only in a wrong version (version-blind
52% vs 39%). It is the same whether the question is dated today (8 of 28
above the hit) or in the past (8 of 28). On expert rulings, all dated today,
it is 6%. A date filter (slice 10) removes every one of these copies by
construction; the prediction for slice 10 starts here.

**Prompt length (A23).** At k = 5 the real prompts are median 846, p90
1,629, max 2,070 cl100k tokens. Longer than the three drift prompts
suggested (406 to 863 by Ollama's count; different tokenizer, different
questions). At A23's measured CPU rates and 180 answer tokens: 45 s per
answer and 7.6 h per 600 at the median, 10.6 h at p90. Still well under the
assumed 15.9 h.

## Slice 6: version-aware retrieval (`as_of` filter before ranking)

One change from the baseline: chunks not in effect on the question's as_of
are removed in SQL before similarity ranks anything. Same embedder, corpus,
questions and k. Run with `make recall METHOD=as-of`, paired against the
baseline with `make recall-compare`.

### Prediction (written 2026-10-02, before the run)

Two are guarantees, not guesses: if either fails, the code is wrong.

| Prediction | Kind | Why |
|---|---|---|
| Wrong-version copy in top k = 0 in every stratum | Guarantee | Every chunk not in effect is filtered out before ranking. |
| No question loses its hit at any k ("A only" = 0) | Guarantee | Exact scan (A2): in-effect chunks keep their order and only lose competitors. |
| version-change recall@5: 39% to about 52% (plausible 45 to 60) | Guess | The 16 questions with a wrong-version copy above the hit get slots back; some of the 7 found only in a wrong version find the right one. |
| expert-ruling recall@5: 44% to about 47% | Guess | Wrong-version copies were in its top 5 for only 16%. |
| version-change change significant (McNemar p < 0.05); FAQ not | Guess | All discordant questions go one way, so about 6 wins are enough (6 of 6 gives p = 0.031). FAQ has 8 questions. |

If version-change gains less than 5 points, wrong-version copies were taking
slots from other wrong chunks, not from the right one, and slice 8 onwards
matters more than this slice.
