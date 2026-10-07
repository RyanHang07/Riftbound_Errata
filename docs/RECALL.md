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

## Slice 9: cross-encoder reranking (bge-reranker-base, ONNX Runtime, CPU)

A31 redesigned this slice: full-text search supplies candidates, a
cross-encoder orders them. Two methods, same candidate budget (40):
- **rerank-vector:** the vector top 40, reranked. What the cross-encoder
  does on its own.
- **rerank:** the vector top 20 plus the full-text top 20 (deduplicated),
  reranked. What full-text candidates add on top.

Baseline: `evals/runs/recall-as-of-qwen3-2026-10-04T1415Z`. Ceilings (right
rule anywhere in the candidates): rerank 91% rulings, 96% version-change.

### Prediction (written 2026-10-04, before any reranked number exists)

| Group | Baseline recall@5 | rerank-vector | rerank | Why |
|---|---|---|---|---|
| expert-ruling | 62% | about 68% | about 70% (63 to 77) | A cross-encoder reads question and rule together; the gap to the 91% ceiling is ordering, which is its job. |
| ruling: cards | 55% | about 60% | about 62% | Full-text candidates found card questions the vector missed (88% union ceiling vs 81%). |
| version-change | 79% | about 82% | about 82% (75 to 88) | Already strong; a general reranker trained on web search may not separate near-identical rule wordings better than qwen3 does. |
| Questions lost | | more than 0 | more than 0 | No guarantee, as with fusion. |
| Significant (McNemar p < 0.05) | | no | **yes on rulings**, no on version-change | An 8-point gain on 160 questions is detected with probability 0.56 to 0.91 (`power.py`). |
| Latency per question, CPU | about 0.05 s | about 2 s | about 2 s | 40 question-passage pairs through a 278M-parameter model on an i5-10600K. |

**When it earns its latency (written now, applied after):** adopt it if
recall@5 gains at least 5 points on rulings or version-change with no
significant loss on either, at under 5 s per question on CPU. A tool a judge
uses at a table can wait 2 to 3 seconds; it cannot wait 30.

### Results: `recall-rerank-qwen3-2026-10-04T1446Z` and `recall-rerank-vector-qwen3-2026-10-06T0459Z`

Both recompute identically from their committed snapshots. Paired with the
qwen3 as-of baseline on the same questions, recall@5:

| Group | Baseline | rerank-vector | rerank (vector + full-text) | rerank gained / lost | McNemar p |
|---|---|---|---|---|---|
| expert-ruling | 62% [55, 70] | 67% [59, 74] | 66% [58, 73] | 24 / 19 | 0.54 |
| expert-ruling-faq | 3/8 | 3/8 | 3/8 | 1 / 1 | 1 |
| version-change | 79% [66, 87] | 86% [74, 93] | 88% [76, 94] | 6 / 1 | 0.13 |
| ruling: cards | 55% | 59% | 58% | 22 / 18 | 0.64 |

rerank-vector against the baseline: rulings 26 gained / 19 lost (p = 0.37),
version-change 5 / 1 (p = 0.22). recall@20 under rerank-vector: version-change
56 of 56.

**Latency, CPU only (ONNX Runtime, i5-10600K):** rerank median 10.5 s per
question (p90 11.9 s); rerank-vector median 12.5 s (p90 14.2 s). The baseline
is about 0.05 s.

### Against the prediction

| Prediction | Result | Verdict |
|---|---|---|
| rerank-vector rulings about 68% | 67% | Right. |
| rerank rulings about 70% (63 to 77) | 66% | Right, low in the range. |
| cards about 60 / 62% | 59 / 58% | Right for rerank-vector, low for rerank. |
| version-change about 82% (75 to 88) | 86 / 88% | Right, top of the range. |
| questions lost: more than 0 | 19 on rulings | Right. |
| rerank significant on rulings | p = 0.54 | **Wrong.** |
| version-change not significant | p = 0.13 / 0.22 | Right. |
| about 2 s per question | 10.5 / 12.5 s | **Wrong by 5 to 6 times.** |

**Decision: not adopted.** The rule written before the run required a
5-point gain on rulings or version-change, no significant loss, *and* under
5 s per question on CPU. Version-change gained 7 to 9 points, but at 10.5 to
12.5 s per question. `as-of` with qwen3 stays the baseline.

**What the run says beyond the decision:**
- **Full-text candidates added nothing.** rerank (vector + full-text) and
  rerank-vector (vector only) are within a question of each other on every
  group. A31's union ceiling (91% / 96%) did not turn into hits: the
  cross-encoder did not pick the full-text finds.
- **The gains are real-looking but unproven.** Version-change 6 gained
  against 1 lost is the right shape, and the question set cannot confirm it
  at this size (power: `docs/POWER.md`).
- **Why it was slow:** 40 question-passage pairs per question through a
  278M-parameter model in full precision, passages up to 512 tokens. Cost
  scales with pairs and model size, so a smaller model or fewer candidates
  are the two levers.
- Card questions moved 3 to 4 points either way. Neither embedders (A29),
  keywords (A31) nor reranking fix them; the corpus has no card text.
  Slice 10 (card database) is the remaining lever.

## Slice 12: failure taxonomy (retrieval)

Every miss at k=5 in `recall-as-of-qwen3-2026-10-04T1415Z` gets exactly one
category, by a fixed rule in `rb_errata/taxonomy.py`. No model reads anything.

| Category | Rule |
|---|---|
| `below-cutoff` | the right rule is in the top 20, at rank 6 to 20 |
| `card-not-in-corpus` | not in the top 20, and the question's source files it under cards (`category: cards`, from the FAQ's `(rulings)/cards/` folder) |
| `rule-only` | not in the top 20, and the source files it under general rules or mechanics |
| `unclassified` | anything else: a failed row, or a question with no source category (all version-change questions, which are written, not mined). Shown, never folded into another |

The card label is a proxy. It says which questions *name* a card; it does not
prove that missing card text caused the miss. Slice 10 tests that.

### Prediction (written 2026-10-07, before the taxonomy is run)

Already known from the committed report, so not predictions: 77 misses
(60 rulings, 5 FAQ, 12 version-change), of which 48 are `below-cutoff` and
29 are outside the top 20.

- Of the 25 ruling and FAQ questions outside the top 20, about **80% are
  `card-not-in-corpus`** (20 of 25). Cards are 71% of those questions and
  retrieve worse.
- `rule-only` about **5**.
- `unclassified` exactly **4**: the version-change questions outside the top
  20, since none has a source category.
- Card questions are a larger share of the outside-top-20 misses than of the
  `below-cutoff` misses: the card text is absent, so the right rule should
  more often never surface at all rather than surface low.

### Results: `evals/runs/recall-as-of-qwen3-2026-10-04T1415Z/taxonomy.md`

`make taxonomy RUN=evals/runs/recall-as-of-qwen3-2026-10-04T1415Z`

| stratum | below-cutoff | card-not-in-corpus | rule-only | unclassified | misses |
|---|---|---|---|---|---|
| expert-ruling | 37 | 21 | 2 | 0 | 60 |
| expert-ruling-faq | 3 | 2 | 0 | 0 | 5 |
| version-change | 8 | 0 | 0 | 4 | 12 |
| **all** | 48 | 23 | 2 | 4 | 77 |

27 of the 48 `below-cutoff` misses sit at rank 6 to 10.

Card share by kind of miss (rulings and FAQ only; cards are 119 of 168 = 71%
of those questions):

| | card questions | share |
|---|---|---|
| outside the top 20 | 23 of 25 | 92% |
| below cutoff (rank 6 to 20) | 32 of 40 | 80% |

### Against the prediction

| Prediction | Result | Verdict |
|---|---|---|
| about 80% of the outside-top-20 ruling misses name a card (20 of 25) | 92% (23 of 25) | Close: the direction and size held, 3 questions over. |
| `rule-only` about 5 | 2 | Close: low, the count is small. |
| `unclassified` exactly 4 | 4 | Right. |
| card share higher outside the top 20 than below the cutoff | 92% against 80% | Right in direction. Not tested for significance: 25 and 40 questions. |

**What it says:**
- **Most misses are ranking, not absence.** 48 of 77 misses (62%) have the
  right rule in the top 20 already. Anything that reorders the top 20 can
  reach them; the reranker (slice 9) did, too slowly. 27 sit at rank 6 to
  10, so a prompt with more passages would also reach them, at the cost of
  prompt length (A23).
- **Only 2 misses are rules questions the search cannot find at all.** On
  rules-only questions the search works; what fails there is order.
- **Card questions dominate both kinds of miss.** 55 of 65 ruling misses
  name a card. Slice 10 (card database) is still the lever, and the test of
  the proxy: if card text in the corpus moves `card-not-in-corpus` questions
  into the top 5 more than it moves the others, the label was right.
- **4 version-change misses cannot be classified** by this rule. That is
  what the bucket is for: it shows the rule's limit instead of hiding it.

## Slice 15: the MCP server

Four tools over stdio, the transport Claude Desktop uses: `search_rules`,
`get_rule`, `list_versions`, `what_changed`. `search_rules` runs the
measured best configuration (`as-of`, qwen3), nothing else. `get_rule` and
`what_changed` read rule text from the local PDFs in `data/raw/`, parsed by
the same code that built the corpus. No rule text enters the repository.

`make mcp-check` starts the server as a subprocess over stdio, exactly as
Claude Desktop does, asks `search_rules` every question at its `as_of`, and
compares the top 5 refs with the committed snapshot
`recall-as-of-qwen3-2026-10-04T1415Z`.

### Prediction (written 2026-10-07, before the server exists)

- **Parity: at least 222 of 224 questions return the same top-5 refs in the
  same order** as the snapshot. Same corpus, same pinned embedder, exact scan;
  any difference should be a near-tie swap from floating-point noise
  (GPU and CPU embeddings can differ in the last digits), not a different
  rule set.
- **Recall@5 through the server equals the snapshot's** on every stratum
  (62% / 38% / 79%), within one question.
- **Warm `search_rules` over stdio: median under 0.3 s on CPU.** The search
  alone took about 0.05 s in slice 9; the protocol adds JSON and a pipe.
- **First `get_rule` or `what_changed` call for a version: about 9 s per
  PDF parsed** (the pypdfium2 figure in `pyproject.toml`), then under 0.1 s
  from the in-process cache. So a first `what_changed` across two versions
  takes about 18 s: slow, and under Claude Desktop's tool timeout.

### Results: `evals/runs/mcp-check-2026-10-07T0200Z` (the user's machine)

224 of 224 questions returned the same top-5 refs in the same order as the
snapshot; recall@5 through the server is identical on every stratum (62% /
38% / 79%). `search_rules` warm: median 0.036 s, p90 0.046 s. First call
8.35 s. First `get_rule` (parses v1.4) 3.05 s, then 0.00 s; first
`what_changed` (parses v1.3) 2.36 s.

### Against the prediction

| Prediction | Result | Verdict |
|---|---|---|
| at least 222 of 224 identical | 224 of 224 | Right. |
| recall@5 equal within one question | identical | Right. |
| warm search median under 0.3 s | 0.036 s | Right, 8 times under. |
| about 9 s per PDF on first use | 3.05 s and 2.36 s | **Wrong by 3 times.** The 9 s in `pyproject.toml` timed the whole first extraction when pypdfium2 was chosen; nothing re-timed it since. |

**What it says:**
- **The server adds nothing to the measured numbers and nothing to the
  ranking.** Zero near-tie swaps: the embeddings are deterministic on this
  machine, so the A29 figures are what a Claude Desktop user gets.
- **The protocol costs about nothing.** 0.036 s per search through the pipe
  is under the 0.05 s the search took in slice 9.
- **The first search is the slow one (8.35 s):** Ollama loading the embedder
  plus the once-per-process pin and corpus checks. Not predicted, and not
  split between the two; a user feels it once per Claude Desktop session.
