"""Cohen's kappa with a bootstrap interval: how far to trust the judge (slice 11).

Kappa is agreement corrected for the agreement chance alone would produce
from each rater's label frequencies. A judge that calls almost everything
"correct" agrees with a human who does the same most of the time, and kappa
is what refuses to call that agreement.

The interval is a percentile bootstrap over the labelled items with a fixed
seed, so the committed report recomputes to the same digits.
"""

from __future__ import annotations

import random
from collections import Counter

SEED = 20261103
RESAMPLES = 2000


def kappa(a: list[str], b: list[str]) -> float | None:
    """Cohen's kappa for two raters over the same items. None when undefined.

    Undefined when chance agreement is 1: both raters used one and the same
    label for every item, so agreement says nothing about skill.
    """
    if len(a) != len(b):
        raise ValueError("raters must label the same items")
    n = len(a)
    if n == 0:
        return None
    observed = sum(x == y for x, y in zip(a, b, strict=True)) / n
    ca, cb = Counter(a), Counter(b)
    expected = sum(ca[k] * cb[k] for k in ca.keys() | cb.keys()) / (n * n)
    if expected == 1:
        return None
    return (observed - expected) / (1 - expected)


def bootstrap(
    a: list[str], b: list[str], resamples: int = RESAMPLES, seed: int = SEED
) -> tuple[float, float] | None:
    """95% percentile interval for kappa; resamples where it is undefined are skipped."""
    rng = random.Random(seed)
    n = len(a)
    values = []
    for _ in range(resamples):
        idx = [rng.randrange(n) for _ in range(n)]
        k = kappa([a[i] for i in idx], [b[i] for i in idx])
        if k is not None:
            values.append(k)
    if len(values) < resamples // 2:
        return None
    values.sort()
    return values[int(0.025 * (len(values) - 1))], values[int(0.975 * (len(values) - 1))]


def landis_koch(k: float) -> str:
    """The conventional reading of a kappa value (Landis and Koch, 1977)."""
    for bound, word in ((0.0, "poor"), (0.2, "slight"), (0.4, "fair"), (0.6, "moderate"),
                        (0.8, "substantial")):  # fmt: skip
        if k <= bound:
            return word
    return "almost perfect"
