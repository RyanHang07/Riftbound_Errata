"""Slice 12: one category for every retrieval miss, by a fixed rule (A41).

A miss is a graded question whose right rule is not in the top 5 (the k the
answer prompt uses). Each miss gets exactly one category, decided from the
committed snapshot and the question's own fields, so a stranger can recompute
every count with no database and no model.

`card-not-in-corpus` is a proxy: the source files the ruling under cards, so
the question names a card whose text the corpus does not hold. It does not
prove that the missing text caused the miss; slice 10 (the card database) is
the test. Questions with no source category, which is every version-change
question (written, not mined), land in `unclassified` rather than being
guessed into a bucket: the bucket exists to show what the rule cannot decide.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from rb_errata import recall
from rb_errata.labels import counterparts as counterparts_mod
from rb_errata.labels.review import load_questions

CUTOFF = recall.PROMPT_K
CATEGORIES = ("below-cutoff", "card-not-in-corpus", "rule-only", "unclassified")
# Source categories that mean "answerable from the rules alone"; anything not
# listed here or under cards is unclassified, never assumed rule-only.
RULE_ONLY = {"general-rules", "mechanics"}


def classify(q: dict[str, Any], g: dict[str, Any]) -> str | None:
    """The miss category for one graded row, or None for a hit. Pure."""
    if g["state"] != "graded":
        return "unclassified"
    rank = g["hit_rank"]
    if rank is not None and rank <= CUTOFF:
        return None
    if rank is not None:  # in the snapshot's top K_MAX, below the cutoff
        return "below-cutoff"
    category = q.get("category")
    if category == "cards":
        return "card-not-in-corpus"
    if category in RULE_ONLY:
        return "rule-only"
    return "unclassified"


def classify_run(run_dir: Path) -> dict[str, dict[str, Any]]:
    """Every miss in a run: id -> {stratum, category, hit_rank}."""
    snap = json.loads((run_dir / "retrieval.json").read_text())
    questions = {q["id"]: q for q in load_questions()}
    cp = counterparts_mod.load()
    out = {}
    for row in snap["results"]:
        q = questions[row["id"]]
        g = recall.grade(q, row, cp)
        c = classify(q, g)
        if c is not None:
            out[q["id"]] = {"stratum": q["stratum"], "category": c, "hit_rank": g.get("hit_rank")}
    return out


def counts(misses: dict[str, dict[str, Any]]) -> dict[str, dict[str, int]]:
    """stratum -> category -> count, every category present (zeros shown)."""
    strata = dict.fromkeys(q["stratum"] for q in load_questions())
    tally = Counter((m["stratum"], m["category"]) for m in misses.values())
    return {s: {c: tally[(s, c)] for c in CATEGORIES} for s in strata}


def report(run_dir: Path) -> list[str]:
    misses = classify_run(run_dir)
    table = counts(misses)
    lines = [
        f"# Failure taxonomy for {run_dir.name}",
        "",
        f"A miss: the right rule (A1) is not in the top {CUTOFF}. One category each,",
        "by the rule in rb_errata/taxonomy.py; no model.",
        "",
        "| stratum | " + " | ".join(CATEGORIES) + " | misses |",
        "|---|" + "---|" * (len(CATEGORIES) + 1),
    ]
    for s, row in table.items():
        lines.append(
            f"| {s} | " + " | ".join(str(row[c]) for c in CATEGORIES) + f" | {sum(row.values())} |"
        )
    total = {c: sum(r[c] for r in table.values()) for c in CATEGORIES}
    lines.append(
        "| **all** | " + " | ".join(str(total[c]) for c in CATEGORIES) + f" | {len(misses)} |"
    )
    below = sorted(m["hit_rank"] for m in misses.values() if m["category"] == "below-cutoff")
    if below:
        near = sum(1 for r in below if r <= 10)
        lines += ["", f"below-cutoff ranks: {near} of {len(below)} at rank 6 to 10."]
    lines += ["", "## Every miss", ""]
    lines += ["| question | stratum | category | rank |", "|---|---|---|---|"]
    for i, m in sorted(misses.items(), key=lambda x: (CATEGORIES.index(x[1]["category"]), x[0])):
        lines.append(f"| {i} | {m['stratum']} | {m['category']} | {m['hit_rank'] or '>20'} |")
    return lines


def write(run_dir: Path) -> Path:
    out = run_dir / "taxonomy.md"
    out.write_text("\n".join(report(run_dir)) + "\n")
    return out
