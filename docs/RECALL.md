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

## Results

Not run yet.
