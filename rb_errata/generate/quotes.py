"""Keep Riot's text out of committed answers (slice 11).

A generated answer may copy a retrieved rule word for word, and answers are
committed so their grading can be audited. Any run of MIN_WORDS or more
consecutive words that also occurs, in order, in a retrieved passage is
replaced with a marker naming that passage. The answer's own reasoning and
its citations survive; the rulebook does not.

Words are compared case-insensitively with punctuation stripped, so a quote
with changed capitalisation or a dropped comma is still caught.
"""

from __future__ import annotations

import re

MIN_WORDS = 10
_WORD = re.compile(r"[A-Za-z0-9']+")


def _norm(word: str) -> str:
    return word.lower().strip("'")


def redact(answer: str, passages: list[tuple[str, str]]) -> tuple[str, int]:
    """(answer with copied runs replaced, number of runs replaced). Pure.

    `passages` are (reference, text) pairs. Greedy and left to right: the
    longest copied run starting at each position is replaced, then the scan
    continues after it.
    """
    spans = [(m.start(), m.end(), _norm(m.group())) for m in _WORD.finditer(answer)]
    words = [w for _, _, w in spans]
    # Every MIN_WORDS-gram of each passage, mapped to the passage it came from.
    grams: dict[tuple[str, ...], str] = {}
    texts: list[tuple[str, list[str]]] = []
    for ref, text in passages:
        pw = [_norm(w) for w in _WORD.findall(text)]
        texts.append((ref, pw))
        for i in range(len(pw) - MIN_WORDS + 1):
            grams.setdefault(tuple(pw[i : i + MIN_WORDS]), ref)

    out, last, count, i = [], 0, 0, 0
    while i <= len(words) - MIN_WORDS:
        hit = grams.get(tuple(words[i : i + MIN_WORDS]))
        if hit is None:
            i += 1
            continue
        # Extend the run while the passage keeps matching.
        j = i + MIN_WORDS
        pw = next(p for r, p in texts if r == hit)
        joined = " " + " ".join(pw) + " "
        while j < len(words) and f" {' '.join(words[i : j + 1])} " in joined:
            j += 1
        out.append(answer[last : spans[i][0]])
        out.append(f"[quoted text from {hit} removed]")
        last = spans[j - 1][1]
        count += 1
        i = j
    out.append(answer[last:])
    return "".join(out), count
