"""Numbers-only export for the public site (A33, A34).

Brief section 2, split write from read: the site never has a number typed
into it. `make site-data` reads the committed runs, questions and dates, and
writes site/data/results.json. Riot's text cannot reach the file: snapshots
hold refs and hashes only, and the questions exported are this project's own
version-change questions (provenance: written), never the CC BY-SA rulings.
"""

from __future__ import annotations

import json
import statistics
from pathlib import Path
from typing import Any

import yaml

from rb_errata import recall, taxonomy
from rb_errata.labels import counterparts as counterparts_mod
from rb_errata.labels.power import mcnemar_p, wilson
from rb_errata.labels.review import load_questions

OUT = Path("site/data/results.json")
RUNS = Path("evals/runs")
PREDICTIONS = Path("evals/predictions.yaml")
EFFECTIVE = Path("data/effective_dates.json")

# The ablation table, in order. Decisions are recorded in docs/BRIEF.md
# (A24 to A38); `paired` names the run each row was compared against.
NAIVE = "recall-2026-10-02T2236Z"
AS_OF = "recall-as-of-2026-10-02T2251Z"
QWEN3 = "recall-as-of-qwen3-2026-10-04T1415Z"
_ROWS = [
    # (run, label, decision, paired against, amendment)
    (NAIVE, "Naive vector search, nomic", "baseline", None, "A24"),
    (AS_OF, "+ date filter", "kept", NAIVE, "A27"),
    (QWEN3, "+ Qwen3 embedder", "best", AS_OF, "A29"),
    ("recall-lexical-qwen3-2026-10-04T1423Z", "Keyword search only", "reference", QWEN3, "A31"),
    (
        "recall-hybrid-qwen3-2026-10-04T1423Z",
        "Hybrid (vector + keyword, RRF)",
        "dropped",
        QWEN3,
        "A31",
    ),
    (
        "recall-rerank-qwen3-2026-10-04T1446Z",
        "Reranker (bge-reranker-base)",
        "dropped",
        QWEN3,
        "A38",
    ),
]
ABLATION: list[dict[str, Any]] = [
    dict(zip(("run", "label", "decision", "paired", "amendment"), r, strict=True)) for r in _ROWS
]


def _graded(run: str) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    snap = json.loads((RUNS / run / "retrieval.json").read_text())
    questions = {q["id"]: q for q in load_questions()}
    cp = counterparts_mod.load()
    return snap, {r["id"]: recall.grade(questions[r["id"]], r, cp) for r in snap["results"]}


def _rate(flags: list[bool]) -> dict[str, Any]:
    k, n = sum(flags), len(flags)
    lo, hi = wilson(k, n)
    return {
        "k": k,
        "n": n,
        "p": round(k / n, 4) if n else None,
        "lo": round(lo, 4),
        "hi": round(hi, 4),
    }


def run_entry(row: dict[str, Any], groups: list[tuple[str, list[str]]]) -> dict[str, Any]:
    snap, g = _graded(row["run"])
    out: dict[str, Any] = {
        **row,
        "method": snap["retrieval"]["method"],
        "embed_model": snap["retrieval"]["embed_model"],
        "groups": {},
    }
    paired = _graded(row["paired"])[1] if row["paired"] else None
    for name, ids in groups:
        ids = [i for i in ids if g.get(i, {}).get("state") == "graded"]
        entry = {
            f"at{k}": _rate(recall._within([g[i]["hit_rank"] for i in ids], k)) for k in recall.KS
        }
        # A20's failure in its sharpest form, the landing page's headline:
        # an outdated copy of the rule ranked above the right one, in the top 5.
        entry["outdated_above_hit5"] = _rate([
            o is not None and o <= 5 and (h is None or o < h)
            for o, h in ((g[i]["outdated_rank"], g[i]["hit_rank"]) for i in ids)
        ])  # fmt: skip
        if paired is not None:
            both = [i for i in ids if paired.get(i, {}).get("state") == "graded"]
            a = recall._within([paired[i]["hit_rank"] for i in both], 5)
            b = recall._within([g[i]["hit_rank"] for i in both], 5)
            gained = sum(1 for x, y in zip(a, b, strict=True) if y and not x)
            lost = sum(1 for x, y in zip(a, b, strict=True) if x and not y)
            entry["vs_paired"] = {
                "gained": gained,
                "lost": lost,
                "p": round(mcnemar_p(gained, gained + lost), 4),
            }
        out["groups"][name.strip()] = entry
    secs = sorted(r["retrieve_s"] for r in snap["results"] if "retrieve_s" in r)
    out["latency_s"] = (
        {"median": round(statistics.median(secs), 3), "p90": secs[int(0.9 * (len(secs) - 1))]}
        if secs
        else None
    )
    return out


def _review() -> dict[str, Any]:
    from rb_errata.labels.review import agreement

    agree, disagree, unsure = agreement()
    n = agree + disagree + unsure
    lo, hi = wilson(agree, n)
    return {"agree": agree, "disagree": disagree, "unsure": unsure, "n": n,
            "lo": round(lo, 4), "hi": round(hi, 4)}  # fmt: skip


def build() -> dict[str, Any]:
    questions = {q["id"]: q for q in load_questions()}
    groups = recall.groups(questions)
    cards = [
        {
            "id": q["id"],
            "question": q["question"],
            "as_of": str(q["as_of"]),
            "ref": q["expect_sources"][0],
        }
        for q in questions.values()
        if q["stratum"] == "version-change"
    ]
    versions = [
        {"version": r["version"], "effective": r["effective"], "basis": r["basis"]}
        for r in json.loads(EFFECTIVE.read_text())
    ]
    return {
        "note": "Generated by `make site-data` from evals/runs. Do not edit by hand.",
        "runs": [run_entry(r, groups) for r in ABLATION],
        "predictions": yaml.safe_load(PREDICTIONS.read_text()),
        "cards": cards,
        "versions": versions,
        "question_counts": {name.strip(): len(ids) for name, ids in groups},
        "review": _review(),
        # A41 slice 12: why the current best run misses, one category each.
        "taxonomy": {
            "run": QWEN3,
            "cutoff": taxonomy.CUTOFF,
            "categories": list(taxonomy.CATEGORIES),
            "counts": taxonomy.counts(taxonomy.classify_run(RUNS / QWEN3)),
        },
    }


def write() -> Path:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(build(), indent=1, sort_keys=False) + "\n")
    return OUT
