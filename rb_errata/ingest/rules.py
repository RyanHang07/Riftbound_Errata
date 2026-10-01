"""Split a rules document's text into numbered rules.

Riftbound rules are numbered like `315.`, `315.2.`, `315.2.b.`, `315.2.b.3.`.
pypdfium2 keeps each rule starting on its own line, so a candidate is any line
that begins with such a number. Two things make candidates unreliable:

- Cross-references: "See rule 467. Scoring" can wrap so a line starts "467.".
- Wrapped lists: "315.2.b.2. 1. The Turn Player..." has a list item inside.

Real rule numbers strictly increase through the document. So the parser keeps
the longest strictly increasing subsequence of candidate numbers, and folds
every rejected candidate back into the text of the rule before it. A single
greedy "must be bigger than the last one" check would be wrong in a costly
way: one stray "467." accepted early would make every real rule up to 467
look out of order, silently dropping hundreds of rules.
"""

from __future__ import annotations

import bisect
import re
from dataclasses import dataclass

# A rule number at the start of a line, followed by whitespace. Components
# alternate freely between digits and single letters: 134.2.a.2.
_NUMBER = re.compile(r"^(\d{3}(?:\.(?:\d+|[a-z]))*)\.(?=\s)")


@dataclass(frozen=True)
class Rule:
    number: str  # "315.2.b", without the trailing dot
    text: str  # the rule's own text, number excluded, whitespace normalised

    @property
    def parts(self) -> tuple[str, ...]:
        return tuple(self.number.split("."))


def sort_key(number: str) -> tuple[int, ...]:
    # Letters rank by alphabet position. Siblings at one level are always the
    # same kind (all digits or all letters), so mixing never decides an order.
    return tuple(int(p) if p.isdigit() else ord(p) - 96 for p in number.split("."))


def _longest_increasing(keys: list[tuple[int, ...]]) -> set[int]:
    """Indices of one longest strictly increasing subsequence. O(n log n)."""
    tails: list[tuple[int, ...]] = []  # smallest tail key for each length
    tail_idx: list[int] = []
    prev = [-1] * len(keys)
    for i, k in enumerate(keys):
        pos = bisect.bisect_left(tails, k)
        if pos == len(tails):
            tails.append(k)
            tail_idx.append(i)
        else:
            tails[pos] = k
            tail_idx[pos] = i
        prev[i] = tail_idx[pos - 1] if pos else -1
    keep, i = set(), (tail_idx[-1] if tail_idx else -1)
    while i != -1:
        keep.add(i)
        i = prev[i]
    return keep


def parse_rules(text: str) -> list[Rule]:
    lines = text.splitlines()
    candidates = [(i, m.group(1)) for i, line in enumerate(lines) if (m := _NUMBER.match(line))]
    keep = _longest_increasing([sort_key(n) for _, n in candidates])
    starts = {line_no: number for j, (line_no, number) in enumerate(candidates) if j in keep}

    rules: list[Rule] = []
    current: str | None = None
    body: list[str] = []

    def flush() -> None:
        if current is not None:
            rules.append(Rule(current, " ".join(" ".join(body).split())))

    for i, line in enumerate(lines):
        if i in starts:
            flush()
            current, body = starts[i], [line[len(starts[i]) + 1 :]]
        elif current is not None:
            body.append(line)  # continuation, or a rejected candidate folded back in
    flush()
    return rules
