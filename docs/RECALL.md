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

### Results: `evals/runs/recall-as-of-2026-10-02T2251Z`, paired with the baseline

| Stratum | Naive recall@5 | As-of recall@5 | Gained | Lost | McNemar p |
|---|---|---|---|---|---|
| expert-ruling (160) | 44% [36, 51] | **58% [50, 65]** | 23 | 0 | 2.4e-07 |
| expert-ruling-faq (8) | 62% | 62% | 0 | 0 | n/a |
| version-change (56) | 39% [28, 52] | **59% [46, 71]** | 11 | 0 | 0.00098 |

recall@20 under as-of: expert-ruling 80% [73, 85], FAQ 8/8, version-change
84% [72, 91].

### Against the prediction

| Prediction | Result | Verdict |
|---|---|---|
| Wrong-version copy in top k = 0 (guarantee) | 0 in every stratum | Held. |
| No question loses its hit (guarantee) | 0 lost | Held. |
| version-change recall@5 about 52% (45 to 60) | 59% | Right, top of the range. |
| expert-ruling recall@5 about 47% | 58% | **Wrong, far too low.** |
| version-change significant, FAQ not | p = 0.00098; FAQ no discordant questions | Right. |

**Why expert rulings gained so much.** The prediction reasoned from the
"wrong-version copy" column (16%), which counts only copies whose text
differs. It ignored copies that differ only in rule numbering. Counted on the
naive run: 63% of expert-ruling top-5 slots (501 of 800) held a chunk not in
effect on the question's date; 72% for version-change. The corpus holds four
versions and the text barely changes between them, so a naive top 5 is
mostly the same rule four times. The date filter's main effect is not
removing wrong answers; it is giving the slots back.

**What is left.** recall@20 is 80 to 84% but recall@5 is 58 to 59%: for about
a quarter of questions the right rule is retrieved but ranked 6th to 20th.
That is a ranking problem, which is what slice 9 (reranking) is for. The
16 to 20% not in the top 20 at all are a finding problem, for slices 7, 8 and
10 (embedder, hybrid search, card database). This run is the baseline every
later slice is measured against.

Prompt length at k = 5 rose to median 988 cl100k tokens (from 846): the
in-effect chunks the filter promotes are longer on average. At A23's CPU
rates: about 49 s per answer, 8.2 h per 600.

## Slice 7: a second embedder, Qwen3-Embedding-0.6B

One change from the slice 6 run: the embedder. Same chunks (the ingest
refuses otherwise), same as_of filter, same questions. nomic-embed-text has
137M parameters; Qwen3-Embedding-0.6B has 0.6B and is trained with an
instruction on the query side only (prefix in `rb_errata/config.py`).
Each embedder's vectors live in their own Postgres schema, so both stay
runnable. Baseline: `evals/runs/recall-as-of-2026-10-02T2251Z`.

### Prediction (written 2026-10-02, before the run)

| Group | Baseline recall@5 | Prediction | Why |
|---|---|---|---|
| expert-ruling | 58% | about 62% (55 to 68) | A larger model; questions and rules use different words. |
| ruling: cards | 52% | about 58%, the largest gain | Card names are League of Legends names; a larger model is more likely to know them. |
| version-change | 59% | about 60%, no real change | Written in rule language already; nomic handles that. |
| Any stratum significant (McNemar p < 0.05) | | **No** | Counted with `power.py`: a 4-point gain on 160 questions is detected with probability 0.15 to 0.28, and a 6-point gain on the 113 card questions 0.23 to 0.42 (discordant rate 10 to 20%). Only a gain near 8 points or more on rulings would likely show. |

So the likely honest outcome is a **null result with its bound**: "no
difference detected; a gain under about 8 points on rulings could not have
been." If Qwen3 is worse, nomic stays the default; if it is better but not
significantly, nomic still stays (cheaper: 768 dims, 4x fewer parameters)
and the difference is recorded.

### Results: `evals/runs/recall-as-of-qwen3-2026-10-04T1415Z`, paired with nomic

| Group | nomic recall@5 | qwen3 recall@5 | qwen3 only | nomic only | McNemar p |
|---|---|---|---|---|---|
| expert-ruling (160) | 58% [50, 65] | 62% [55, 70] | 23 | 16 | 0.34 |
| expert-ruling-faq (8) | 5/8 | 3/8 | 0 | 2 | 0.5 |
| version-change (56) | 59% [46, 71] | **79% [66, 87]** | 12 | 1 | **0.0034** |
| ruling: cards (113) | 52% [43, 61] | 55% [46, 64] | 18 | 15 | 0.73 |
| ruling: general rules (26) | 62% | 73% | 4 | 1 | 0.38 |
| ruling: mechanics (21) | 86% | 90% | 1 | 0 | 1 |

recall@20 under qwen3: expert-ruling 86% [79, 90], version-change 93% [83, 97].

### Against the prediction

| Prediction | Result | Verdict |
|---|---|---|
| expert-ruling about 62% (55 to 68) | 62% | Right. |
| cards about 58%, the largest gain | 55% (+3); general rules gained most (+11) | **Wrong** on "largest". |
| version-change about 60%, no real change | 79% (+20) | **Wrong, badly.** |
| No stratum significant | version-change p = 0.0034 | **Wrong.** |

**Why version-change was mispredicted.** The reasoning was "already written
in rule language, so nomic handles it". The numbers say the opposite: these
questions turn on small wording changes between versions ("countered",
"finalized"), and the larger model separates near-identical rules better.
The prediction treated vocabulary match as the whole problem; precision
between near-duplicates was the bigger part.

**Card questions did not move** (52% to 55%, 18 gained against 15 lost).
The two embedders find *different* card questions, not more of them. A
larger embedder does not fix the card gap, which supports slice 10 (a card
database) over hoping a model knows card names. It also hints at slice 8:
the union of the two models' hits on rulings is 116 of 160 (73%), against
62% for the better one alone, so combining rankers has room to work.

**The pre-written decision rule** said nomic stays unless Qwen3 is
significantly better. It is, on version-change, the stratum the project
exists for, and not worse anywhere it can be measured (FAQ lost 2 of 8; with
n = 8 that is p = 0.5). Speed is the same on the user's machine (23 vs 21
ms per chunk). The switch of default is the user's decision (A29).

## Slice 8: hybrid search (vector + Postgres full-text, fused by RRF)

Two new methods, both with the as_of filter on every list:
- **lexical:** Postgres full-text search alone. The question's stemmed terms
  are ORed (an AND of every word matches nothing), ranked by `ts_rank_cd`
  with length normalisation.
- **hybrid:** reciprocal rank fusion of the vector top 50 and the full-text
  top 50, score = sum of 1 / (60 + rank) (Cormack, Clarke and Buettcher,
  SIGIR 2009). The constant 60 is the paper's and is not tuned, because
  tuning it on these questions would overfit them.

Baseline: `evals/runs/recall-as-of-qwen3-2026-10-04T1415Z` (A30).

### Prediction (written 2026-10-04, before any lexical or hybrid number exists)

| Group | qwen3 as-of recall@5 | lexical alone | hybrid | Why |
|---|---|---|---|---|
| expert-ruling | 62% | about 40% | about 65% (60 to 70) | Card names are not in the corpus, so keywords miss what vectors miss; the gain comes from exact rule words. |
| ruling: cards | 55% | about 30% | about 57% | Same: no card text to match. Slice 10's job. |
| version-change | 79% | about 55% | about 78%, no gain | The vector list is already strong; fusing a weaker list can push hits down as easily as up. |
| Questions lost (qwen3 only) | | | **more than 0**, about 5 to 10 on rulings | Unlike the date filter, fusion has no guarantee: a weak list can demote a hit. |
| Any stratum significant | | | **No** | Same power limits as slice 7. |

The slice 7 hint (the union of two embedders' hits is 73% on rulings) says
combining rankers *can* help, but that union came from two strong rankers.
If hybrid beats the prediction by more than 5 points on rulings, keywords
carry more signal than the card-name gap suggested; if it loses on
version-change, fusion needs weighting, which slice 9 (reranking) replaces
anyway.

### Results: `recall-hybrid-qwen3-2026-10-04T1423Z` and `recall-lexical-qwen3-2026-10-04T1423Z`

**Reproducibility check passed.** Full-text search does not use the embedder,
so the user's lexical run and one made in the cloud session (different
machine, different schema) must agree. All 224 ranked lists are identical,
scores included.

| Group | qwen3 as-of | lexical | hybrid | hybrid gained / lost | McNemar p |
|---|---|---|---|---|---|
| expert-ruling | 62% [55, 70] | 53% [45, 61] | 66% [59, 73] | 22 / 16 | 0.42 |
| expert-ruling-faq | 3/8 | 3/8 | 5/8 | 3 / 1 | 0.63 |
| version-change | **79% [66, 87]** | 34% [23, 47] | **66% [53, 77]** | 1 / 8 | **0.039** |
| ruling: cards | 55% | 49% | 60% | 21 / 15 | 0.41 |
| ruling: general rules | 73% | 62% | 77% | 1 / 0 | 1 |
| ruling: mechanics | 90% | 67% | 86% | 0 / 1 | 1 |

### Against the prediction

| Prediction | Result | Verdict |
|---|---|---|
| lexical rulings about 40% | 53% | **Wrong, too low.** |
| lexical cards about 30% | 49% | **Wrong, far too low.** |
| lexical version-change about 55% | 34% | **Wrong, too high.** |
| hybrid rulings about 65% (60 to 70) | 66% | Right. |
| hybrid cards about 57% | 60% | Close. |
| hybrid version-change about 78%, no gain | 66%, 8 lost against 1 gained | **Wrong: it got significantly worse.** |
| questions lost: more than 0, 5 to 10 on rulings | 16 on rulings | Direction right, size wrong. |
| nothing significant | version-change loss p = 0.039 | **Wrong.** |

**What the misses mean.** Keywords are better on card questions than
assumed: a card ruling still uses rule words ("countered", "attach",
"chosen"), and those match. Keywords are much worse on version-change
questions, which are phrased in plain language around a small wording
change; the stemmed terms match many rules equally. Fusing a list that weak
into the strongest one costs the version-change stratum 13 points, the one
the project exists for.

**Decision: hybrid is not adopted.** The pre-written rule was "if it loses
on version-change, fusion needs weighting, which slice 9 replaces anyway".
It lost, significantly. `as-of` with qwen3 stays the baseline.

**What it leaves for slice 9.** The two lists find different things. The
right rule is in the union of the vector top 20 and the lexical top 20 for
91% [86, 95] of rulings (vector alone: 86%), 88% of card questions (81%) and
96% [88, 99] of version-change questions (93%). So full-text search is a
good *candidate source* and a bad *ranker*. Slice 9 uses it that way: both
lists supply up to 40 candidates and a cross-encoder reranker picks the top
5, instead of rank fusion.

Prompt length at k = 5: median 1,362 cl100k tokens under hybrid and 1,789
under lexical, against 825 under vector: full-text favours long chunks even
with length normalisation.
