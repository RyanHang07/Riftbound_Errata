# Power analysis for the labelled set

*2026-10-02, run before the set was finalised (brief section 2). Reproduce
with `make power`; the code is `rb_errata/labels/power.py`, exact
calculations with the standard library.*

## Precision: 95% Wilson half-width, percentage points

| n | p = 0.5 | p = 0.7 | p = 0.9 |
|:--|:--|:--|:--|
| 8 | 28.5 | 26.0 | 22.4 |
| 20 | 20.1 | 18.7 | 13.7 |
| 40 | 14.8 | 13.7 | 9.5 |
| 60 | 12.3 | 11.3 | 7.7 |
| 100 | 9.6 | 8.8 | 6.0 |
| 160 | 7.7 | 7.0 | 4.7 |

## Detection: paired exact McNemar test, alpha 0.05

Two retrieval configurations on the same questions. `p_d` is the share of
questions where they disagree; 90% of disagreements favour the new one. The
smallest significant result is 6 disagreeing questions, all one way.

| n | p_d 0.05 | p_d 0.10 | p_d 0.20 | p_d 0.30 |
|:--|:--|:--|:--|:--|
| 20 | 0.00 | 0.01 | 0.10 | 0.32 |
| 40 | 0.01 | 0.11 | 0.52 | 0.79 |
| 60 | 0.04 | 0.31 | 0.78 | 0.95 |
| 100 | 0.21 | 0.67 | 0.97 | 1.00 |
| 160 | 0.51 | 0.91 | 1.00 | 1.00 |

## What it means for this set

| Stratum | n | Verdict |
|:--|:--|:--|
| expert-ruling | 160 | ±7.7 points at worst: meets the brief's ±10. Carries the overall naive vs version-aware comparison if about 1 question in 10 changes outcome (power 0.91). |
| expert-ruling-faq | 8 | ±28 points: reported as a side note only. |
| version-change | 20 | **Too small.** At most 0.32 power even for a large effect. The specific claim that date-awareness fixes stale answers needs about **60** (30 rules, each asked at two dates): 0.78 to 0.95 power for 20-30% disagreement. |
| review sample | 20 | 18 of 20 agreeing gives 70% to 97%. Wide, but a real bound; extend to 40 if disagreements appear. |

`p_d` itself is unknown until slice 5 runs. Slice 3 suggests it is not small
on version questions (outdated rule ranked first in 3 of 10 chosen
candidates), but those were selected because their rules changed, so that is
not an estimate. These numbers are planning figures, not results.
