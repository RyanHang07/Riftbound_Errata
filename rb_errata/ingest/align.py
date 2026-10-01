"""Match each rule to its counterpart in another version, by text, not number.

Rule numbers are not stable between versions (SPIKE_1 finding 4: Stun is 410
in v1.1 and 423 in v1.4), so numbers can never join versions (A16). Text can:

1. Identical text: the same rule, possibly renumbered.
2. Otherwise, the most similar rule above a threshold: the same rule, edited.
3. No counterpart above the threshold: removed (old side) or added (new side).

Similarity is Jaccard overlap of word 3-grams ("shingles"). An inverted index
from shingle to rules keeps it near-linear: only rules sharing at least one
shingle are ever compared, instead of every old rule against every new one.
This is the light version slice 3 needs to find changed rules; `what_changed`
(slice 12) will reuse it and is where it gets hardened.
"""

from __future__ import annotations

import difflib
import re
from collections import defaultdict
from dataclasses import dataclass

from rb_errata.ingest.rules import Rule

# Below this, two rules are treated as different rules rather than an edit.
MATCH_THRESHOLD = 0.5
# Words whose appearance or disappearance usually flips a rule's meaning.
# Used only to rank the report for human review, never to decide anything.
_FLIP_WORDS = {
    "not", "no", "cannot", "can't", "can", "may", "must", "only", "never",
    "always", "instead", "unless", "except", "before", "after", "each", "any", "all",
}  # fmt: skip
_WORD = re.compile(r"[A-Za-z0-9']+")


def _shingles(text: str) -> set[tuple[str, ...]]:
    w = [x.lower() for x in _WORD.findall(text)]
    if len(w) < 3:
        return {tuple(w)} if w else set()
    return {tuple(w[i : i + 3]) for i in range(len(w) - 2)}


def jaccard(a: set[tuple[str, ...]], b: set[tuple[str, ...]]) -> float:
    return len(a & b) / len(a | b) if a or b else 1.0


@dataclass(frozen=True)
class Match:
    old: Rule
    new: Rule | None  # None: removed
    similarity: float

    @property
    def kind(self) -> str:
        if self.new is None:
            return "removed"
        if self.old.text == self.new.text:
            return "same" if self.old.number == self.new.number else "moved"
        return "changed"


def align(old: list[Rule], new: list[Rule]) -> tuple[list[Match], list[Rule]]:
    """Every old rule's match, plus the new rules nothing matched (added)."""
    by_text: dict[str, list[Rule]] = defaultdict(list)
    for r in new:
        by_text[r.text].append(r)
    new_sh = [_shingles(r.text) for r in new]
    index: dict[tuple[str, ...], list[int]] = defaultdict(list)
    for i, sh in enumerate(new_sh):
        for s in sh:
            index[s].append(i)

    matches: list[Match] = []
    used: set[str] = set()
    for r in old:
        exact = [n for n in by_text.get(r.text, []) if n.number not in used]
        if exact:
            # Prefer the same number when the text appears more than once.
            pick = next((n for n in exact if n.number == r.number), exact[0])
            used.add(pick.number)
            matches.append(Match(r, pick, 1.0))
            continue
        sh = _shingles(r.text)
        candidates = {i for s in sh for i in index.get(s, [])}
        best, best_sim = None, 0.0
        for i in candidates:
            sim = jaccard(sh, new_sh[i])
            if sim > best_sim:
                best, best_sim = new[i], sim
        if best is not None and best_sim >= MATCH_THRESHOLD:
            used.add(best.number)
            matches.append(Match(r, best, best_sim))
        else:
            matches.append(Match(r, None, best_sim))
    added = [n for n in new if n.number not in used]
    return matches, added


def word_diff(a: str, b: str) -> str:
    """Compact word-level diff: [-removed-] {+added+}."""
    out: list[str] = []
    for op in difflib.ndiff(a.split(), b.split()):
        tag, word = op[:2], op[2:]
        if tag == "- ":
            out.append(f"[-{word}-]")
        elif tag == "+ ":
            out.append(f"{{+{word}+}}")
        elif tag == "  ":
            out.append(word)
    return re.sub(r"-\] \[-", " ", re.sub(r"\+\} \{\+", " ", " ".join(out)))


# Cross-references ("See rule 185.") and step labels ("9.") change with every
# renumbering. Found on the first diff run: they dominated the ranking, so
# they are blanked before scoring. Display diffs still show them.
_XREF = re.compile(r"\b(?:rules?|step)\s+\d+(?:\.\w+)*\.?|^\d+\.\s", re.IGNORECASE)


def normalise(text: str) -> str:
    return _XREF.sub("rule #", text)


def flip_score(a: str, b: str) -> int:
    """How many meaning-flipping words or numbers changed. For ranking only."""
    wa = [x.lower() for x in _WORD.findall(normalise(a))]
    wb = [x.lower() for x in _WORD.findall(normalise(b))]
    changed = set(wa) ^ set(wb)
    return sum(1 for w in changed if w in _FLIP_WORDS or w.isdigit())
