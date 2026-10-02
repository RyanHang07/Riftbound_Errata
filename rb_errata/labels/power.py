"""How many questions are needed, computed before the set is finalised.

Brief section 2: "Before writing 100 labelled questions, work out how many are
actually needed." Two questions, both answered exactly with the standard
library, no simulation:

1. Precision: how wide is a 95% Wilson interval on a proportion (recall@k,
   answer accuracy, review agreement) for a stratum of n questions?
2. Detection: comparing two retrieval configurations on the SAME questions
   (brief: pair on the question), what is the chance an exact McNemar test
   at alpha 0.05 detects a real improvement of a given size?

McNemar only looks at discordant questions: those one configuration gets
right and the other wrong. If a fraction p_d of questions are discordant and
a share q of those favour the new configuration, the number discordant is
Binomial(n, p_d), and the test is an exact two-sided binomial test of q = 0.5
on them.
"""

from __future__ import annotations

import math

Z = 1.959963984540054  # 95%


def wilson(k: int, n: int) -> tuple[float, float]:
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    centre = (p + Z * Z / (2 * n)) / (1 + Z * Z / n)
    half = Z * math.sqrt(p * (1 - p) / n + Z * Z / (4 * n * n)) / (1 + Z * Z / n)
    return (max(0.0, centre - half), min(1.0, centre + half))


def half_width(p: float, n: int) -> float:
    lo, hi = wilson(round(p * n), n)
    return (hi - lo) / 2


def _binom_pmf(k: int, n: int, p: float) -> float:
    return math.comb(n, k) * p**k * (1 - p) ** (n - k)


def mcnemar_rejects(wins: int, d: int, alpha: float = 0.05) -> bool:
    """Exact two-sided binomial test of wins out of d discordant at p = 0.5."""
    if d == 0:
        return False
    tail = min(wins, d - wins)
    p = 2 * sum(_binom_pmf(i, d, 0.5) for i in range(tail + 1))
    return min(1.0, p) < alpha


def mcnemar_power(n: int, p_discordant: float, q_favour: float, alpha: float = 0.05) -> float:
    total = 0.0
    for d in range(n + 1):
        pd = _binom_pmf(d, n, p_discordant)
        if pd < 1e-12:
            continue
        reject = sum(
            _binom_pmf(w, d, q_favour) for w in range(d + 1) if mcnemar_rejects(w, d, alpha)
        )
        total += pd * reject
    return total


def min_discordant_all_one_way(alpha: float = 0.05) -> int:
    d = 1
    while not mcnemar_rejects(d, d, alpha):
        d += 1
    return d


def report() -> list[str]:
    out = ["Precision: 95% Wilson half-width, in percentage points", ""]
    sizes = [8, 20, 40, 60, 100, 160, 188]
    out.append("  n     " + "  ".join(f"p={p:.1f}" for p in (0.5, 0.7, 0.9)))
    for n in sizes:
        out.append(
            f"  {n:<5} " + "  ".join(f"{100 * half_width(p, n):5.1f}" for p in (0.5, 0.7, 0.9))
        )
    out += ["", f"Smallest significant McNemar result: {min_discordant_all_one_way()} discordant "
            "questions, all favouring one configuration.", ""]  # fmt: skip
    out.append(
        "Detection: power of a paired McNemar test (alpha 0.05), q = 0.9 of discordant favour new"
    )
    out.append("  n     " + "  ".join(f"p_d={p:.2f}" for p in (0.05, 0.10, 0.20, 0.30)))
    for n in (20, 40, 60, 100, 160):
        row = "  ".join(f"{mcnemar_power(n, p, 0.9):8.2f}" for p in (0.05, 0.10, 0.20, 0.30))
        out.append(f"  {n:<5} {row}")
    return out
