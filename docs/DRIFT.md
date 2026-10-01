# Slice 3: naive retrieval and temporal drift

*Runs of 2026-10-01. Evidence: `evals/fixtures/drift-2026-10-01/` (first run,
with `CORRECTION.md`) and `evals/fixtures/drift-2026-10-01T1906Z/` (second
run). Every fixture holds rule references, validity windows, distances and
content hashes, never rule text; `make show F=<fixture>` re-displays the text
on a machine with the corpus.*

## The failure, captured

Asked on 2026-10-01 **"When does my Rune Pool empty during my turn?"**, naive
retrieval (vector search over every Core Rules version, no date filter)
returned:

| Rank | Passage | In effect on 2026-10-01? |
|:--|:--|:--|
| 1 | `core@1.2:163.1` | no (Dec 2025 to Mar 2026) |
| 2 | `core@1.1:160.1` | no (Oct to Dec 2025) |
| 3 | `core@1.4:167.1` | **yes** |
| 4 | `core@1.3:166.1` | no (Mar to Jul 2026) |

The rule changed on 2026-07-24: the pool used to empty at the end of the draw
phase, and now empties at the start of the Main Phase. Given these passages,
`qwen3:4b-instruct-2507` answered:

> Your Rune Pool empties at the end of your draw phase and at the end of your
> turn [core@1.2:163.1]. It also empties at the start of your Main Phase
> [core@1.4:167.1]. Any unspent Energy or Power are lost in each case
> [core@1.2:163.1].

Confident, cited, and wrong: it presents a rule that stopped applying two
months earlier as current, alongside the rule that replaced it. **The current
passage was retrieved. The answer is still wrong**, because three outdated
copies of the same rule were retrieved with it, and a 4B model given several
versions does not know which one wins. That is the case for filtering by date
*before* ranking (brief section 5), demonstrated rather than asserted.

## How candidates were chosen

1. `make diff` aligned every rule with its counterpart in the current version
   by text, so renumbered rules still pair up.
2. Candidates were picked by reading the changes, keeping only those where the
   answer to a player's question flips. Not by running searches first.
3. Each was traced through every version, and `stale` lists exactly the
   versions that give the old answer. After the first run exposed a
   mislabel, every label was re-verified on full rule texts
   (`make check-candidates`).
4. A prediction was written in `evals/drift_candidates.yaml` before each run.
5. The top-ranked passage is graded three ways: **captured** (an outdated
   version that gives a different answer), **not captured** (the current
   rule), **inconclusive** (anything else). Every candidate's fixture is kept,
   hit or miss.

## Results

| Candidate | Changed in | Verdict | Current rule's rank |
|:--|:--|:--|:--|
| rune-pool-empties | v1.4 | **captured** | 3 |
| replacement-effect-order | v1.4 | **captured** | 3 |
| accelerate-two-domains | v1.4 | **captured** | 4 |
| gear-to-battlefield | v1.4 | not captured | 1 |
| countered-spell-played | v1.4 | not captured | 1 |
| deflect-chosen-twice | v1.3 | inconclusive: right answer, outdated version | 3 |
| legion-countered-spell | v1.4 | inconclusive: rule not retrieved | absent |
| teammate-spells-2v2 | v1.3 | inconclusive: rule not retrieved | absent |
| legend-leave-zone | v1.4 | inconclusive: rule not retrieved | absent |
| c-cost-two-domains | v1.4 | inconclusive: rule not retrieved | absent |

**Predictions against outcomes.**
- Batch 1 (first four): predicted 1 or 2 captured; **0**. The run first
  recorded one capture; it came from a mislabelled candidate and was
  re-graded (`drift-2026-10-01/CORRECTION.md`).
- Batch 2 (last six): predicted 2 to 4 captured; **3**. Of the two named
  likeliest misses, one missed (c-cost) and one was captured (accelerate).

**What the three captured answers did.**
- rune-pool: blended outdated and current rules, both cited (above).
- replacement-effect-order: answered correctly from the current passage at
  rank 3, despite the outdated one ranking first.
- accelerate-two-domains: said yes, then argued itself to no (the current
  answer), and was cut off at the 400-token limit.

## What this does and does not show

**Shows:** naive retrieval puts outdated rules first for real questions
(3 of 10 here), and a small model given mixed versions can state an outdated
rule as current, with citations.

**Does not show a rate.** Ten hand-picked candidates, chosen because their
rules changed, are not a sample of the questions people ask. How often this
happens is slice 5's job, on a labelled set sized by power analysis.

**Two findings slice 3 was not looking for:**
1. **Missing the rule entirely was as common as returning the outdated one:**
   in 4 of 10, the answering rule was not in the top 5, because naive search
   matched a surface word ("Legion", "2v2") elsewhere. That is the target of
   hybrid search and reranking (slices 8-9).
2. **"Found the right passage" is not enough.** In all three captures the
   current rule was in the top 5, so the version-aware recall@5 of A1 would
   score them as hits; one answer was still wrong. The evaluation needs to
   measure outdated passages retrieved alongside the right one, not only
   whether the right one appeared.
