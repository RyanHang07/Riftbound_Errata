# Correction to the 2026-10-01 drift run

The four fixtures in this folder are stored exactly as the run wrote them.
One recorded verdict is wrong because the candidate label behind it was wrong.

| Candidate | Recorded | Re-graded with corrected labels |
|:--|:--|:--|
| deflect-chosen-twice | captured | **inconclusive** |
| gear-to-battlefield | not captured | not captured |
| legion-countered-spell | inconclusive | inconclusive |
| teammate-spells-2v2 | inconclusive | inconclusive |

**What was wrong.** The Deflect candidate listed `core@1.3:809.1.c` as stale.
v1.3 already says the extra cost applies "for each time they choose me", so it
gives the same answer to the question as v1.4. The per-choice wording arrived
in v1.3; v1.4 changed "choose" to "target". Ranking v1.3 first is "right
answer, outdated version", which the candidate rules grade inconclusive.

**How it was found.** By reading the evidence: the generated answer quoted the
v1.3 line that contradicts the label.

**Why it happened.** The cross-version trace printed rule texts cut at 140
characters. The deciding words start at character 170.

**Fix.** `make check-candidates` prints every candidate rule in full, in every
version, labelled. All four candidates were re-checked with it; only Deflect
was mislabelled. `make regrade D=evals/fixtures/drift-2026-10-01` reproduces
the table above from the stored rankings, without re-running any search.
