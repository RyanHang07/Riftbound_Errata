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
import time
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
from rb_errata.retrieve.methods import METHODS, retrieve

RUNS = Path("evals/runs")
CORPUS = Path("data/corpus.json")
K_MAX = 20
KS = (1, 3, 5, 10, 20)
PROMPT_K = 5  # the k the answer prompt uses; its length feeds the A23 budget


def _fingerprint(rows: list[tuple[str, str, str, str | None]]) -> str:
    """Text hash, ref and validity window of every chunk, order-free.

    Dates are part of it on purpose. Found while building slice 6: a database
    ingested before the A17 date decision had every chunk's text right and
    v1.3's valid_from wrong. A text-only check passed it, and the date filter
    would have been measured on dates nobody can see in data/corpus.json.
    """
    lines = sorted(f"{h} {ref} {start} {end}" for h, ref, start, end in rows)
    return hashlib.sha256("\n".join(lines).encode()).hexdigest()


def _db_corpus(settings: Settings) -> str:
    with db.connect(settings) as conn:
        rows = conn.execute(
            "SELECT content_hash, source_ref, valid_from, valid_to "
            f"FROM {settings.db_schema}.chunks"
        ).fetchall()
    return _fingerprint([(str(h), str(r), str(f), str(t) if t else None) for h, r, f, t in rows])


def _manifest_corpus() -> str:
    chunks = json.loads(CORPUS.read_text())["chunks"]
    return _fingerprint(
        [(c["content_hash"], c["source_ref"], c["valid_from"], c["valid_to"]) for c in chunks]
    )


def run(settings: Settings, method: str = "naive") -> Path:
    if method not in METHODS:
        raise SystemExit(f"unknown method {method!r}; one of {sorted(METHODS)}")
    client = Ollama(settings)
    try:
        embed_digest = checked_digest(client, settings.embed_model, settings.embed_digest)
    finally:
        client.close()
    reranker = None
    if method.startswith("rerank"):
        from rb_errata.retrieve import rerank

        # Before any search or file write, as for Ollama pins: an unpinned or
        # changed model refuses here, not halfway through the questions.
        reranker = rerank.load(settings)
    # Idempotent: adds what later slices need (the full-text column, slice 8)
    # to a database ingested before they existed, without re-embedding.
    db.init(settings)
    # The report cites data/corpus.json. A database ingested differently
    # (another chunker, a missing version) would make every number describe a
    # corpus nobody can inspect, so the run refuses rather than warns.
    if _db_corpus(settings) != _manifest_corpus():
        raise SystemExit(
            "database chunks (text, refs or validity dates) differ from data/corpus.json; "
            "run `make ingest` first"
        )

    from rb_errata.ingest.pipeline import token_counter

    count = token_counter()
    # Minute-stamped and never overwritten, as with drift fixtures.
    stamp = datetime.now(UTC).strftime("%Y-%m-%dT%H%MZ")
    out_dir = RUNS / f"recall-{method}-{settings.embed_profile}-{stamp}"
    if out_dir.exists():
        raise SystemExit(f"{out_dir} already exists; wait a minute and rerun")
    questions = load_questions()
    results = []
    client = Ollama(settings)
    try:
        for q in questions:
            row: dict[str, Any] = {"id": q["id"]}
            try:
                as_of = date.fromisoformat(str(q["as_of"]))
                t0 = time.perf_counter()
                ranked = retrieve(method, settings, client, q["question"], K_MAX, as_of)
                row["retrieve_s"] = round(time.perf_counter() - t0, 4)
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
            "method": METHODS[method],
            "method_id": method,
            "reranker": reranker,
            "rerank_candidates": settings.rerank_candidates if reranker else None,
            "cpu_only": settings.cpu_only,
            "k_max": K_MAX,
            "embed_model": settings.embed_model,
            "embed_digest": embed_digest,
            "embed_profile": settings.embed_profile,
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

    by_id = {x["id"]: x for x in graded if x["state"] == "graded"}
    lines += ["", "## recall@5 by group", "", "| group | recall@5 |", "|---|---|"]
    for name, members in groups(questions):
        ranks = [by_id[i]["hit_rank"] for i in members if i in by_id]
        lines.append(f"| {name} | {_cell(_within(ranks, 5))} |")

    secs = sorted(r["retrieve_s"] for r in snap["results"] if "retrieve_s" in r)
    if secs:
        lines += [
            "",
            "## Retrieval latency per question (embedding + SQL + rerank)",
            "",
            f"median {statistics.median(secs) * 1000:.0f} ms, "
            f"p90 {secs[int(0.9 * (len(secs) - 1))] * 1000:.0f} ms, max {secs[-1] * 1000:.0f} ms "
            f"over {len(secs)} questions. The first question includes model loading.",
        ]

    tokens = sorted(x["prompt_tokens_cl100k"] for x in graded if x.get("prompt_tokens_cl100k"))
    if tokens:
        lines += [
            "",
            f"## Prompt length at k={PROMPT_K} (for the A23 budget)",
            "",
            f"cl100k tokens over {len(tokens)} prompts: median {statistics.median(tokens):.0f}, "
            f"p90 {tokens[int(0.9 * (len(tokens) - 1))]}, max {tokens[-1]}. "
            "cl100k is not the generator's tokenizer; Ollama's own counts come with "
            "generation (slice 11).",
        ]
    return lines


def groups(questions: dict[str, dict[str, Any]]) -> list[tuple[str, list[str]]]:
    """Strata, then expert rulings by category: question ids per row.

    The category split is the A25 finding (card questions 35% recall@5 under
    the naive search, mechanics 86%), so slices 7 to 10 report it every time
    rather than recount it by hand. Sub-rows of a stratum, never pooled.
    """
    out = []
    for s in dict.fromkeys(q["stratum"] for q in questions.values()):
        out.append((s, [i for i, q in questions.items() if q["stratum"] == s]))
    rulings = {i: q for i, q in questions.items() if q["stratum"] == "expert-ruling"}
    for c in sorted({str(q.get("category")) for q in rulings.values()}):
        out.append(
            (f"  ruling: {c}", [i for i, q in rulings.items() if str(q.get("category")) == c])
        )
    return out


def compare(a_dir: Path, b_dir: Path, k: int = 5) -> list[str]:
    """Pair two runs on the same questions: discordant counts and exact McNemar.

    Only questions both runs graded are paired; a question unknown in either
    run is left out of both, never counted as a loss.
    """
    from rb_errata.labels.power import mcnemar_p

    snaps = [json.loads((d / "retrieval.json").read_text()) for d in (a_dir, b_dir)]
    for key in ("questions_sha256", "corpus_chunks_sha256"):
        if snaps[0][key] != snaps[1][key]:
            # Different questions or a different corpus: the pairing would be
            # between two experiments, not two configurations.
            raise SystemExit(f"runs differ in {key}; they cannot be paired")
    questions = {q["id"]: q for q in load_questions()}
    cp = counterparts_mod.load()
    graded = [{r["id"]: grade(questions[r["id"]], r, cp) for r in s["results"]} for s in snaps]
    names = [f"{x['retrieval']['method']}; {x['retrieval']['embed_model']}" for x in snaps]
    lines = [
        f"# {b_dir.name} vs {a_dir.name}, recall@{k}",
        "",
        f"A = {a_dir.name} ({names[0]}); B = {b_dir.name} ({names[1]}).",
        "Exact two-sided McNemar on the discordant questions. Wilson 95% in brackets.",
        "",
        f"| stratum | A recall@{k} | B recall@{k} | B only | A only | McNemar p |",
        "|---|---|---|---|---|---|",
    ]
    for s, members in groups(questions):
        ids = [i for i in members if all(g.get(i, {}).get("state") == "graded" for g in graded)]
        a = _within([graded[0][i]["hit_rank"] for i in ids], k)
        b = _within([graded[1][i]["hit_rank"] for i in ids], k)
        b_only = sum(1 for x, y in zip(a, b, strict=True) if y and not x)
        a_only = sum(1 for x, y in zip(a, b, strict=True) if x and not y)
        p = mcnemar_p(b_only, b_only + a_only)
        lines.append(
            f"| {s} | {_cell(a)} | {_cell(b)} | {b_only} | {a_only} | "
            + (f"{p:.3g} |" if b_only + a_only else "n/a |")
        )
    return lines
