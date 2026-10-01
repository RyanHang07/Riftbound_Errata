"""Group numbered rules into chunks for embedding. Deliberately simple.

This is the baseline chunker the brief asks for in slice 2. It will be
replaced, and nothing downstream depends on its shape: every chunk records the
full list of rule numbers it contains (`refs`), and a recall hit is "the
expected rule number is in a retrieved chunk's refs, at the right version"
(A1, A16). Re-chunking therefore never invalidates a label.

Scheme: one chunk per second-level rule (315.2 with all of 315.2.*). The
top-level heading (315.) is prefixed to each of its chunks, so a chunk about
"315.2" still says which phase it belongs to. A group over the token cap is
split at rule boundaries.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from rb_errata.ingest.rules import Rule

# Measured in cl100k tokens. nomic-embed-text tokenizes differently, and with
# `truncate: false` an over-long input errors instead of being silently cut
# (A6). 400 leaves wide margin under nomic's 2048-token window in Ollama.
# The cap applies between rules: a single rule is never split, so one long
# rule can exceed it (v1.4 has a 510-token chunk). HARD_LIMIT catches a rule
# long enough to threaten the embedder's window, which would mean the parser
# merged rules it should have separated.
MAX_TOKENS = 400
HARD_LIMIT = 1500


@dataclass(frozen=True)
class Chunk:
    source_ref: str  # the group's number, e.g. "315.2"
    refs: tuple[str, ...]  # every rule number inside, e.g. ("315.2", "315.2.a", ...)
    text: str


def _make(key: str, heading: Rule | None, rules: list[Rule], text: str) -> Chunk:
    # The heading's number is in refs too. Found on the first real run: without
    # it, 244 of v1.4's 2,381 rules (every heading) belonged to no chunk, so a
    # label naming a heading could never be retrieved.
    refs = ((heading.number,) if heading else ()) + tuple(r.number for r in rules)
    return Chunk(key, refs, text)


def _render(heading: Rule | None, rules: list[Rule]) -> str:
    lines = [f"{heading.number}. {heading.text}"] if heading else []
    lines += [f"{r.number}. {r.text}" for r in rules]
    return "\n".join(lines)


def chunk_rules(rules: list[Rule], count_tokens: Callable[[str], int]) -> list[Chunk]:
    headings = {r.number: r for r in rules if len(r.parts) == 1}
    has_children = {r.parts[0] for r in rules if len(r.parts) > 1}
    groups: dict[str, list[Rule]] = {}
    for r in rules:
        # Top-level rules with no children still form their own group, so no
        # rule is ever dropped. (000. Golden and Silver Rules has children.)
        key = ".".join(r.parts[:2])
        if len(r.parts) == 1 and r.number in has_children:
            continue  # a heading; it is prefixed to its children instead
        groups.setdefault(key, []).append(r)

    chunks: list[Chunk] = []
    for key, members in groups.items():
        top = key.split(".")[0]
        heading = headings.get(top) if "." in key else None
        batch: list[Rule] = []
        for r in members:
            if batch and count_tokens(_render(heading, [*batch, r])) > MAX_TOKENS:
                chunks.append(_make(key, heading, batch, _render(heading, batch)))
                batch = []
            batch.append(r)
        if batch:
            chunks.append(_make(key, heading, batch, _render(heading, batch)))
    for c in chunks:
        if count_tokens(c.text) > HARD_LIMIT:
            raise ValueError(
                f"chunk {c.source_ref} exceeds {HARD_LIMIT} tokens; parser merged rules?"
            )
    return chunks
