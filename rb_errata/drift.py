"""Slice 3: capture naive retrieval answering with an outdated rule.

Each candidate in evals/drift_candidates.yaml names a rule whose meaning
changed, the version-qualified refs that say the old thing (`stale`) and the
ones that say the current thing (`current`). Chosen from `make diff`, by
reading the changes, not by running searches first.

Verdict on the top-ranked result, three states (never two):
- captured: it carries a `stale` ref. The first thing a user sees is out of
  date and says something different from today's rule.
- not captured: it carries a `current` ref.
- inconclusive: neither. This includes an older version whose meaning
  matches today's rule (the 2v2 teammate rule changed in v1.3, so a v1.3
  result is stale by version but right in meaning), and an unrelated rule.

Every candidate gets a fixture, captured or not. Keeping only the hits would
show that the failure can happen while hiding how often it does not.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import yaml

from rb_errata import db
from rb_errata.config import Settings
from rb_errata.generate import prompt
from rb_errata.ollama import Ollama, checked_digest
from rb_errata.retrieve.vector import Passage, search

CANDIDATES = Path("evals/drift_candidates.yaml")
FIXTURES = Path("evals/fixtures")
K = 5
ANSWER_TOKENS = 400


@dataclass(frozen=True)
class Candidate:
    id: str
    question: str
    as_of: date
    current: frozenset[str]
    stale: frozenset[str]
    change: str


def load_candidates(path: Path = CANDIDATES) -> list[Candidate]:
    rows = yaml.safe_load(path.read_text())
    out = []
    for r in rows:
        c = Candidate(
            r["id"], r["question"], date.fromisoformat(str(r["as_of"])),
            frozenset(r["current"]), frozenset(r["stale"]), r["change"],
        )  # fmt: skip
        if c.current & c.stale:
            raise ValueError(f"{c.id}: a ref cannot be both current and stale")
        out.append(c)
    return out


def verdict(c: Candidate, ranked: list[Passage]) -> str:
    top = ranked[0].qualified_refs if ranked else set()
    if top & c.stale:
        return "captured"
    if top & c.current:
        return "not captured"
    return "inconclusive"


def regrade(f: dict[str, Any], c: Candidate) -> str:
    """Re-grade a stored fixture against (possibly corrected) labels.

    The fixture keeps every ranked result's version-qualified refs, so a label
    fix never needs the search re-run: the evidence is fixed, only the
    reading of it changes, and both stay on record.
    """
    if not f["results"]:
        return "inconclusive"
    top = f["results"][0]
    doc = top["source_ref"].split(":", 1)[0]
    refs = {f"{doc}:{r}" for r in top["refs"]}
    if refs & c.stale:
        return "captured"
    if refs & c.current:
        return "not captured"
    return "inconclusive"


def _first_rank(c_refs: frozenset[str], ranked: list[Passage]) -> int | None:
    return next((i + 1 for i, p in enumerate(ranked) if p.qualified_refs & c_refs), None)


def fixture(
    c: Candidate, ranked: list[Passage], v: str, settings: Settings, embed_digest: str,
    generation: dict[str, Any] | None,
) -> dict[str, Any]:  # fmt: skip
    """Everything about the run except Riot's text: refs, dates, hashes, ranks."""
    return {
        "id": c.id,
        "question": c.question,
        "as_of": c.as_of.isoformat(),
        "captured_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "verdict": v,
        "change": c.change,
        "current": sorted(c.current),
        "stale": sorted(c.stale),
        "first_current_rank": _first_rank(c.current, ranked),
        "first_stale_rank": _first_rank(c.stale, ranked),
        "retrieval": {
            "method": "naive-vector, no date filter",
            "k": K,
            "embed_model": settings.embed_model,
            "embed_digest": embed_digest,
            "query_prefix": settings.embed_query_prefix,
        },
        "results": [
            {
                "rank": i + 1,
                "source_ref": p.source_ref,
                "refs": p.refs,
                "valid_from": p.valid_from.isoformat(),
                "valid_to": p.valid_to.isoformat() if p.valid_to else None,
                "in_effect_on_as_of": p.in_effect_on(c.as_of),
                "distance": round(p.distance, 4),
                "content_hash": p.content_hash,
            }
            for i, p in enumerate(ranked)
        ],
        "generation": generation,
    }


def _generate(
    settings: Settings, client: Ollama, c: Candidate, ranked: list[Passage]
) -> dict[str, Any]:
    digest = checked_digest(client, settings.gen_model, settings.gen_digest)
    g = client.generate(prompt.build(c.question, ranked), max_tokens=ANSWER_TOKENS)
    return {
        "model": settings.gen_model,
        "digest": digest,
        "think": settings.gen_think,
        "temperature": settings.gen_temperature,
        "seed": settings.gen_seed,
        "num_ctx": settings.gen_num_ctx,
        "cpu_only": settings.cpu_only,
        "prompt_template_sha256": prompt.TEMPLATE_SHA256,
        "prompt_tokens": g.prompt_tokens,
        "answer_tokens": g.answer_tokens,
        # The model's own words. They may quote a rule they were given; that
        # is the only place passage wording can reach a committed file.
        "answer": g.text.strip(),
    }


def run(settings: Settings) -> list[str]:
    # One folder per run, stamped to the minute: a rerun never overwrites an
    # earlier run's evidence, including evidence later found to be misread.
    # (A date alone was not enough: the second run happened the same day.)
    out_dir = FIXTURES / f"drift-{datetime.now(UTC).strftime('%Y-%m-%dT%H%MZ')}"
    if out_dir.exists():
        raise SystemExit(f"{out_dir} already exists; wait a minute and rerun")
    out_dir.mkdir(parents=True)
    client = Ollama(settings)
    lines = []
    try:
        embed_digest = checked_digest(client, settings.embed_model, settings.embed_digest)
        for c in load_candidates():
            ranked = search(settings, client, c.question, K)
            v = verdict(c, ranked)
            gen = _generate(settings, client, c, ranked) if v == "captured" else None
            (out_dir / f"{c.id}.json").write_text(
                json.dumps(fixture(c, ranked, v, settings, embed_digest, gen), indent=2) + "\n"
            )
            top = ranked[0]
            lines.append(
                f"{v:<14}{c.id:<28}#1 {top.source_ref} "
                f"({'in effect' if top.in_effect_on(c.as_of) else 'NOT in effect'} on {c.as_of}); "
                f"current first at #{_first_rank(c.current, ranked) or '-'}"
            )
    finally:
        client.close()
    return lines


def regrade_dir(path: Path) -> list[str]:
    cands = {c.id: c for c in load_candidates()}
    lines = []
    for p in sorted(path.glob("*.json")):
        f = json.loads(p.read_text())
        c = cands.get(f["id"])
        now = regrade(f, c) if c else "no candidate"
        flag = "" if now == f["verdict"] else "   <- CHANGED by corrected labels"
        lines.append(f"{f['id']:<28} recorded {f['verdict']:<14} now {now}{flag}")
    return lines


def check_candidates() -> list[str]:
    """Full text of every rule a candidate names, in every version, for review.

    Never truncated: truncation is how the Deflect label error got through.
    Each line says how the candidate classifies that version. Prints Riot's
    text to the local terminal only.
    """
    from rb_errata.ingest.align import align
    from rb_errata.ingest.fetch import RAW
    from rb_errata.ingest.pdf import extract_text
    from rb_errata.ingest.rules import parse_rules
    from rb_errata.ingest.sources import CORE_RULES

    rules = {
        d.version: parse_rules(extract_text(RAW / d.filename))
        for d in CORE_RULES
        if (RAW / d.filename).exists()
    }
    latest = CORE_RULES[-1].version
    out = []
    for c in load_candidates():
        out.append(f"\n===== {c.id}: {c.question}")
        for ref in sorted(c.current):
            ver, num = ref.split("@", 1)[1].split(":")
            text = next((r.text for r in rules[ver] if r.number == num), "(missing)")
            out.append(f"  CURRENT {ref}\n      {text}")
            if ver != latest:
                continue
            # Every older version's counterpart of this rule, labelled.
            for v, rs in rules.items():
                if v == latest:
                    continue
                for m in align(rs, rules[latest])[0]:
                    if m.new is not None and m.new.number == num:
                        q = f"core@{v}:{m.old.number}"
                        label = (
                            "stale" if q in c.stale else "current" if q in c.current else "NEITHER"
                        )
                        out.append(f"  {label:<7} {q}\n      {m.old.text}")
    return out


def show(settings: Settings, path: Path) -> list[str]:
    """Re-display a fixture with rule text pulled from the local database.

    The fixture holds hashes, not text. A hash that is no longer in the
    database means the corpus changed since capture, and is reported.
    """
    f = json.loads(path.read_text())
    out = [f"{f['id']}: {f['verdict'].upper()}", f"Q (as of {f['as_of']}): {f['question']}", ""]
    with db.connect(settings) as conn:
        for r in f["results"]:
            row = conn.execute(
                "SELECT text FROM chunks WHERE source_ref = %s AND content_hash = %s",
                (r["source_ref"], r["content_hash"]),
            ).fetchone()
            effect = "in effect" if r["in_effect_on_as_of"] else "NOT IN EFFECT"
            out.append(
                f"#{r['rank']} {r['source_ref']}  [{effect} on {f['as_of']}]  d={r['distance']}"
            )
            text = str(row[0]) if row else "(text not in local database: corpus changed?)"
            out.append("   " + text[:500].replace("\n", "\n   "))
            out.append("")
    if f["generation"]:
        out += [f"ANSWER ({f['generation']['model']}):", f["generation"]["answer"]]
    return out
