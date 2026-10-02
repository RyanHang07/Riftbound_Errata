"""Slice 5: recall@k with Wilson intervals, the retrieval baseline. No generation.

Split write from read (brief section 2). `run` needs the database and the
embedder and writes one snapshot per run: every question's top K_MAX results
as refs, dates and hashes, never Riot's text. `report` reads only committed
files (the snapshot, evals/questions.yaml, evals/counterparts.json), so every
number can be recomputed by a stranger with no database and no model.

A hit (A1, A16): a retrieved chunk that carries an expected version-qualified
ref AND is in effect on the question's as_of. Three states per question: hit,
miss, or unknown when the search itself errored. Unknown never enters a
denominator. Strata are reported separately and never pooled.

Two secondary columns, which the headline never uses:
- wrong-version copy@k (A20's "stale contamination"): an aligned copy of an
  expected rule, from a version not in effect on as_of and with different
  text, is in the top k. For a question dated today that copy is outdated;
  for one dated in the past it can also be a newer version, equally wrong on
  that date. The slice 3 captures were all hits by A1 and one answer was
  still wrong because of it.
- version-blind recall@k: the original brief's definition, which counts any
  version. The gap between it and recall@k is what A1 exists to see.
"""

from __future__ import annotations

import hashlib
import json
import statistics
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from rb_errata import db
from rb_errata.config import Settings
from rb_errata.generate import prompt
from rb_errata.labels import counterparts as counterparts_mod
from rb_errata.labels.power import wilson
from rb_errata.labels.review import load_questions
from rb_errata.ollama import Ollama, checked_digest
from rb_errata.retrieve.vector import search

RUNS = Path("evals/runs")
CORPUS = Path("data/corpus.json")
K_MAX = 20
KS = (1, 3, 5, 10, 20)
PROMPT_K = 5  # the k the answer prompt uses; its length feeds the A23 budget


def _hash_set(hashes: list[str]) -> str:
    return hashlib.sha256("\n".join(sorted(hashes)).encode()).hexdigest()


def _db_corpus(settings: Settings) -> str:
    with db.connect(settings) as conn:
        rows = conn.execute("SELECT content_hash FROM chunks").fetchall()
    return _hash_set([str(r[0]) for r in rows])


def _manifest_corpus() -> str:
    return _hash_set([c["content_hash"] for c in json.loads(CORPUS.read_text())["chunks"]])


def run(settings: Settings) -> Path:
    client = Ollama(settings)
    try:
        embed_digest = checked_digest(client, settings.embed_model, settings.embed_digest)
    finally:
        client.close()
    # The report cites data/corpus.json. A database ingested differently
    # (another chunker, a missing version) would make every number describe a
    # corpus nobody can inspect, so the run refuses rather than warns.
    if _db_corpus(settings) != _manifest_corpus():
        raise SystemExit("database chunks differ from data/corpus.json; run `make ingest` first")

    from rb_errata.ingest.pipeline import token_counter

    count = token_counter()
    # Minute-stamped and never overwritten, as with drift fixtures.
    out_dir = RUNS / f"recall-{datetime.now(UTC).strftime('%Y-%m-%dT%H%MZ')}"
    if out_dir.exists():
        raise SystemExit(f"{out_dir} already exists; wait a minute and rerun")
    questions = load_questions()
    results = []
    client = Ollama(settings)
    try:
        for q in questions:
            row: dict[str, Any] = {"id": q["id"]}
            try:
                ranked = search(settings, client, q["question"], K_MAX)
            except Exception as exc:
                row["error"] = f"{type(exc).__name__}: {exc}"[:300]
                results.append(row)
                continue
            row["prompt_tokens_cl100k"] = count(prompt.build(q["question"], ranked[:PROMPT_K]))
            row["ranked"] = [
                {
                    "source_ref": p.source_ref,
                    "refs": p.refs,
                    "valid_from": p.valid_from.isoformat(),
                    "valid_to": p.valid_to.isoformat() if p.valid_to else None,
                    "distance": round(p.distance, 4),
                    "content_hash": p.content_hash,
                }
                for p in ranked
            ]
            results.append(row)
    finally:
        client.close()

    out_dir.mkdir(parents=True)
    snapshot = {
        "captured_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "retrieval": {
            "method": "naive-vector, no date filter",
            "k_max": K_MAX,
            "embed_model": settings.embed_model,
            "embed_digest": embed_digest,
            "query_prefix": settings.embed_query_prefix,
        },
        "corpus_chunks_sha256": json.loads(CORPUS.read_text())["chunks_sha256"],
        "questions_sha256": hashlib.sha256(Path("evals/questions.yaml").read_bytes()).hexdigest(),
        "prompt_template_sha256": prompt.TEMPLATE_SHA256,
        "results": results,
    }
    (out_dir / "retrieval.json").write_text(json.dumps(snapshot, indent=1) + "\n")
    (out_dir / "report.md").write_text("\n".join(report(out_dir)) + "\n")
    return out_dir


# --- read side: committed files only ----------------------------------------


def _in_effect(r: dict[str, Any], day: date) -> bool:
    start = date.fromisoformat(r["valid_from"])
    end = date.fromisoformat(r["valid_to"]) if r["valid_to"] else None
    return start <= day and (end is None or day < end)


def _qualified(r: dict[str, Any]) -> set[str]:
    doc = r["source_ref"].split(":", 1)[0]
    return {f"{doc}:{x}" for x in r["refs"]}


def first_rank(
    ranked: list[dict[str, Any]], wanted: set[str], day: date, *, in_effect: bool | None
) -> int | None:
    """1-based rank of the first chunk carrying a wanted ref, or None.

    in_effect True: only chunks in effect on `day` count (A1's hit).
    in_effect False: only chunks NOT in effect count (an outdated copy).
    None: either (version-blind).
    """
    for i, r in enumerate(ranked):
        if in_effect is not None and _in_effect(r, day) != in_effect:
            continue
        if _qualified(r) & wanted:
            return i + 1
    return None


def grade(
    q: dict[str, Any], row: dict[str, Any], cp: dict[str, list[dict[str, Any]]]
) -> dict[str, Any]:
    """One question's ranks. Pure; unit-tested."""
    if "error" in row:
        return {"id": q["id"], "stratum": q["stratum"], "state": "unknown"}
    day = date.fromisoformat(str(q["as_of"]))
    expect = set(q["expect_sources"])
    copies = {c["ref"] for s in expect for c in cp.get(s, []) if not c["same_text"]}
    any_copy = {c["ref"] for s in expect for c in cp.get(s, [])}
    ranked = row["ranked"]
    return {
        "id": q["id"],
        "stratum": q["stratum"],
        "state": "graded",
        "hit_rank": first_rank(ranked, expect, day, in_effect=True),
        "outdated_rank": first_rank(ranked, copies, day, in_effect=False),
        "blind_rank": first_rank(ranked, expect | any_copy, day, in_effect=None),
        "prompt_tokens_cl100k": row.get("prompt_tokens_cl100k"),
    }


def _within(ranks: list[int | None], k: int) -> list[bool]:
    return [r is not None and r <= k for r in ranks]


def _cell(flags: list[bool]) -> str:
    n = len(flags)
    if n == 0:
        return "n/a"
    hits = sum(flags)
    lo, hi = wilson(hits, n)
    return f"{hits}/{n} = {hits / n:.0%} [{lo:.0%}, {hi:.0%}]"


def report(run_dir: Path) -> list[str]:
    snap = json.loads((run_dir / "retrieval.json").read_text())
    questions = {q["id"]: q for q in load_questions()}
    cp = counterparts_mod.load()
    graded = [grade(questions[r["id"]], r, cp) for r in snap["results"]]
    strata = list(dict.fromkeys(q["stratum"] for q in questions.values()))

    meta = snap["retrieval"]
    lines = [
        f"# Recall run {run_dir.name}",
        "",
        f"{meta['method']}; {meta['embed_model']} @ {meta['embed_digest'][:12]}; "
        f"corpus {snap['corpus_chunks_sha256'][:12]}; questions {snap['questions_sha256'][:12]}.",
        "Hit = expected version-qualified ref, in effect on as_of (A1). Wilson 95% in brackets.",
        "",
        "## recall@k (headline)",
        "",
        "| stratum | " + " | ".join(f"@{k}" for k in KS) + " | unknown |",
        "|---|" + "---|" * (len(KS) + 1),
    ]
    for s in strata:
        g = [x for x in graded if x["stratum"] == s and x["state"] == "graded"]
        unknown = sum(1 for x in graded if x["stratum"] == s and x["state"] == "unknown")
        ranks = [x["hit_rank"] for x in g]
        lines.append(
            f"| {s} | " + " | ".join(_cell(_within(ranks, k)) for k in KS) + f" | {unknown} |"
        )

    lines += [
        "",
        "## Secondary at k=5 (never the headline)",
        "",
        "| stratum | recall@5 | version-blind recall@5 | wrong-version copy in top 5 "
        "| wrong-version copy ranked above the hit |",
        "|---|---|---|---|---|",
    ]
    for s in strata:
        g = [x for x in graded if x["stratum"] == s and x["state"] == "graded"]
        # The slice 3 failure in its sharpest form: the first version of the
        # rule a reader meets is the outdated one.
        above = [
            o is not None and o <= 5 and (h is None or o < h)
            for o, h in ((x["outdated_rank"], x["hit_rank"]) for x in g)
        ]
        lines.append(
            f"| {s} | {_cell(_within([x['hit_rank'] for x in g], 5))} "
            f"| {_cell(_within([x['blind_rank'] for x in g], 5))} "
            f"| {_cell(_within([x['outdated_rank'] for x in g], 5))} | {_cell(above)} |"
        )

    tokens = sorted(x["prompt_tokens_cl100k"] for x in graded if x.get("prompt_tokens_cl100k"))
    if tokens:
        lines += [
            "",
            f"## Prompt length at k={PROMPT_K} (for the A23 budget)",
            "",
            f"cl100k tokens over {len(tokens)} prompts: median {statistics.median(tokens):.0f}, "
            f"p90 {tokens[int(0.9 * (len(tokens) - 1))]}, max {tokens[-1]}. "
            "cl100k is not the generator's tokenizer; Ollama's own counts come with slice 6.",
        ]
    return lines
