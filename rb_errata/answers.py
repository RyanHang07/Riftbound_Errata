"""Slice 11: generate an answer for every question, then measure them.

Three steps, each its own make target, so any can be redone alone:

1. `make answers`: the current best retrieval (as-of, k = 5) and the pinned
   generator for every question. Each answer records the prompt and template
   hashes, the model digest, every setting, and where the model ran (GPU
   share from Ollama; A41: runs on the GPU, timing claims from the CPU only).
   Copied runs of rule text are removed before anything is written
   (generate/quotes.py).
2. `make answer-sample RUN=...`: a seeded, stratified sample of answers whose
   retrieval hit, written to evals/answer_review.yaml for the user to label.
   Drawn without looking at any judge verdict, and the file shows none, so
   the hand labels are blind to the judge.
3. `make judge RUN=...` (rb_errata/judge.py), then `make answers-report`.

Accuracy is conditioned on retrieval (brief section 3): over questions whose
right rule was in the top 5. The unconditioned figure is shown beside it.
"""

from __future__ import annotations

import hashlib
import json
import random
import statistics
import sys
import time
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import yaml

from rb_errata import db, recall
from rb_errata.config import Settings
from rb_errata.generate import prompt
from rb_errata.generate.quotes import redact
from rb_errata.labels import counterparts as counterparts_mod
from rb_errata.labels.agreement import bootstrap, kappa, landis_koch
from rb_errata.labels.power import wilson
from rb_errata.labels.review import load_questions

K = recall.PROMPT_K
METHOD = "as-of"
REVIEW = Path("evals/answer_review.yaml")
SAMPLE_SEED = 20261103
# Per stratum, from questions whose retrieval hit. 60 labels give kappa an
# interval about +/- 0.2 wide at moderate agreement: enough to tell "usable"
# from "not", which is the decision this sample exists for.
SAMPLE = {"expert-ruling": 40, "expert-ruling-faq": 3, "version-change": 17}


def _row(passages: list[Any]) -> dict[str, Any]:
    """Passages in a snapshot row's shape, so recall.grade applies unchanged."""
    return {"ranked": [
        {"source_ref": p.source_ref, "refs": list(p.refs), "valid_from": p.valid_from.isoformat(),
         "valid_to": p.valid_to.isoformat() if p.valid_to else None}
        for p in passages
    ]}  # fmt: skip


PARTIAL = "answers.partial.json"
# What must match for a resumed run to be one experiment, not two spliced.
SAME = ("generator", "template_sha256", "retrieval", "corpus_chunks_sha256", "questions_sha256")


def run(settings: Settings, limit: int | None = None, resume: Path | None = None) -> Path:
    """Answer every question, saving after each one.

    Found on the first full run: Ollama dropped a connection at question ~50
    and every answer so far was lost. Now each answer is written to
    answers.partial.json as it is made, and `make answers RESUME=<dir>`
    continues a stopped run, refusing if anything that defines the experiment
    (generator, prompt, retrieval, corpus, questions) has changed.
    """
    from rb_errata.ollama import Ollama, checked_digest
    from rb_errata.retrieve.methods import retrieve

    client = Ollama(settings)
    try:
        gen_digest = checked_digest(client, settings.gen_model, settings.gen_digest)
        embed_digest = checked_digest(client, settings.embed_model, settings.embed_digest)
    finally:
        client.close()
    db.init(settings)
    if recall._db_corpus(settings) != recall._manifest_corpus():
        raise SystemExit("database differs from data/corpus.json; run `make ingest` first")
    meta: dict[str, Any] = {
        "generator": {"model": settings.gen_model, "digest": gen_digest,
                      "think": settings.gen_think, "temperature": settings.gen_temperature,
                      "seed": settings.gen_seed, "num_ctx": settings.gen_num_ctx,
                      "max_tokens": settings.gen_max_tokens},
        "template_sha256": prompt.TEMPLATE_SHA256,
        "retrieval": {"method": METHOD, "k": K, "embed_model": settings.embed_model,
                      "embed_digest": embed_digest},
        "corpus_chunks_sha256": json.loads(recall.CORPUS.read_text())["chunks_sha256"],
        "questions_sha256": hashlib.sha256(
            Path("evals/questions.yaml").read_bytes()).hexdigest(),
    }  # fmt: skip
    rows: list[dict[str, Any]] = []
    placement, retries = None, 0
    if resume is not None:
        saved = json.loads((resume / PARTIAL).read_text())
        changed = [k for k in SAME if saved[k] != meta[k]]
        if changed:
            raise SystemExit(
                f"cannot resume {resume}: {', '.join(changed)} changed since it started"
            )
        out_dir, rows = resume, saved["answers"]
        placement, retries = saved["placement"]["gpu_fraction"], saved.get("ollama_retries", 0)
    else:
        stamp = datetime.now(UTC).strftime("%Y-%m-%dT%H%MZ")
        out_dir = recall.RUNS / f"answers-{settings.embed_profile}-{stamp}"
        if out_dir.exists():
            raise SystemExit(f"{out_dir} already exists; wait a minute and rerun")
        out_dir.mkdir(parents=True)

    def save(name: str) -> None:
        (out_dir / name).write_text(json.dumps({
            "captured_at": datetime.now(UTC).isoformat(timespec="seconds"), **meta,
            # A41: GPU and CPU can produce different text at temperature 0, so a
            # comparison must never mix placements. Recorded, never assumed.
            "placement": {"gpu_fraction": placement, "cpu_only": settings.cpu_only},
            "ollama_retries": retries,
            "answers": rows,
        }, indent=1) + "\n")  # fmt: skip

    done_ids = {r["id"] for r in rows}
    questions = load_questions()[:limit] if limit else load_questions()
    cp = counterparts_mod.load()
    client = Ollama(settings)
    try:
        started = time.perf_counter()
        for n, q in enumerate(questions, 1):
            if q["id"] in done_ids:
                continue
            if n == 1 or n % 20 == 0:
                spent = time.perf_counter() - started
                print(f"  answer {n}/{len(questions)}, {spent:.0f}s elapsed", file=sys.stderr,
                      flush=True)  # fmt: skip
            day = date.fromisoformat(str(q["as_of"]))
            passages = retrieve(METHOD, settings, client, q["question"], K, day)
            text = prompt.build(q["question"], passages)
            g = client.generate(text, max_tokens=settings.gen_max_tokens)
            if placement is None:
                placement = client.loaded_vram_fraction(settings.gen_model)
            answer, quoted = redact(g.text.strip(), [(p.source_ref, p.text) for p in passages])
            graded = recall.grade(q, _row(passages), cp)
            rows.append({
                "id": q["id"],
                "stratum": q["stratum"],
                "retrieved": [p.source_ref for p in passages],
                # Slice 13's signals: distances for margin, every rule number
                # inside the chunks for "cites only what was retrieved".
                "distances": [round(p.distance, 4) for p in passages],
                "retrieved_refs": sorted(set().union(*(p.qualified_refs for p in passages))),
                "hit_rank": graded["hit_rank"],
                "prompt_sha256": hashlib.sha256(text.encode()).hexdigest(),
                "prompt_tokens": g.prompt_tokens,
                "answer_tokens": g.answer_tokens,
                "prompt_s": round(g.prompt_ns / 1e9, 3),
                "answer_s": round(g.answer_ns / 1e9, 3),
                "load_s": round(g.load_ns / 1e9, 3),
                "done_reason": g.done_reason,
                "quotes_removed": quoted,
                "answer": answer,
            })  # fmt: skip
            retries = client.retries + (saved.get("ollama_retries", 0) if resume else 0)
            save(PARTIAL)
    except BaseException:
        print(f"\nstopped after {len(rows)} answers, saved in {out_dir / PARTIAL}.\n"
              f"Continue with: make answers RESUME={out_dir}", file=sys.stderr)  # fmt: skip
        raise
    finally:
        client.close()
    save("answers.json")
    (out_dir / PARTIAL).unlink()
    (out_dir / "report.md").write_text("\n".join(report(out_dir)) + "\n")
    return out_dir


# --- the blind hand-label sample -------------------------------------------------


def draw(answers: list[dict[str, Any]], plan: dict[str, int], seed: int) -> list[str]:
    """Seeded sample of answer ids whose retrieval hit, per stratum. Pure.

    Takes the answers only: it cannot look at judge verdicts, so it cannot
    be biased towards easy or hard cases for the judge.
    """
    rng = random.Random(seed)
    out = []
    for stratum, n in plan.items():
        pool = sorted(a["id"] for a in answers
                      if a["stratum"] == stratum and a["hit_rank"] is not None
                      and a["hit_rank"] <= K)  # fmt: skip
        out += rng.sample(pool, min(n, len(pool)))
    return out


def sample(run_dir: Path) -> Path:
    if REVIEW.exists() and any(i.get("verdict") for i in _review_items()):
        raise SystemExit(f"{REVIEW} already has verdicts; move it aside to draw a new sample")
    from rb_errata.judge import reference

    snap = json.loads((run_dir / "answers.json").read_text())
    by_id = {a["id"]: a for a in snap["answers"]}
    questions = {q["id"]: q for q in load_questions()}
    items = []
    for i in draw(snap["answers"], SAMPLE, SAMPLE_SEED):
        q = questions[i]
        items.append({"id": i, "verdict": None, "note": "", "question": q["question"],
                      "as_of": str(q["as_of"]), "reference": reference(q),
                      "answer": by_id[i]["answer"]})  # fmt: skip
    header = (
        "# Hand labels for slice 11 (judge validation). Blind: no judge verdict is shown.\n"
        "# For each item, read the question, the expert's reference answer, then the\n"
        "# generated answer, and set `verdict` to one of:\n"
        "#   correct       same conclusion as the reference\n"
        "#   incorrect     a different or contradicting conclusion\n"
        "#   not_answered  no conclusion, or says the information is not available\n"
        "# Ignore style, length and citations. `note` is optional.\n"
        f"# Drawn from {run_dir.name} with seed {SAMPLE_SEED}; `make answers-report` reads it.\n"
    )
    REVIEW.write_text(
        header
        + yaml.safe_dump(
            {"run": run_dir.name, "items": items}, sort_keys=False, allow_unicode=True, width=100
        )
    )
    return REVIEW


def _review_items() -> list[dict[str, Any]]:
    if not REVIEW.exists():
        return []
    items: list[dict[str, Any]] = (yaml.safe_load(REVIEW.read_text()) or {}).get("items", [])
    return items


# --- report ------------------------------------------------------------------------


def _cell(flags: list[bool]) -> str:
    if not flags:
        return "n/a"
    k, n = sum(flags), len(flags)
    lo, hi = wilson(k, n)
    return f"{k}/{n} = {k / n:.0%} [{lo:.0%}, {hi:.0%}]"


def _judgments(run_dir: Path) -> list[tuple[str, dict[str, Any]]]:
    return [(p.stem.removeprefix("judgments-"), json.loads(p.read_text()))
            for p in sorted(run_dir.glob("judgments-*.json"))]  # fmt: skip


def report(run_dir: Path) -> list[str]:
    snap = json.loads((run_dir / "answers.json").read_text())
    answers = snap["answers"]
    gen, place = snap["generator"], snap["placement"]
    where = (
        "CPU only"
        if place["cpu_only"]
        else (
            f"{place['gpu_fraction']:.0%} on GPU"
            if place["gpu_fraction"] is not None
            else "unknown"
        )
    )
    lines = [
        f"# Answers {run_dir.name}",
        "",
        f"{gen['model']} @ {gen['digest'][:12]}; think {gen['think']}, temperature "
        f"{gen['temperature']}, seed {gen['seed']}, num_ctx {gen['num_ctx']}, max "
        f"{gen['max_tokens']} tokens; template {snap['template_sha256'][:12]}; retrieval "
        f"{snap['retrieval']['method']} k={snap['retrieval']['k']}; placement: {where}.",
        "",
    ]
    total = [a["prompt_s"] + a["answer_s"] for a in answers]
    p90 = sorted(total)[int(0.9 * (len(total) - 1))]
    lines += [
        "## Generation",
        "",
        f"{len(answers)} answers. Seconds per answer (prefill + decode, Ollama's clock): "
        f"median {statistics.median(total):.2f}, p90 {p90:.2f}."
        f" Answer tokens: median {statistics.median(a['answer_tokens'] for a in answers):.0f}.",
        f"Ollama connections dropped and retried: {snap.get('ollama_retries', 0)}. "
        f"Stopped at the token cap: {sum(a['done_reason'] == 'length' for a in answers)}. "
        f"Answers with copied rule text removed: {sum(a['quotes_removed'] > 0 for a in answers)}.",
        "",
    ]
    strata = list(dict.fromkeys(a["stratum"] for a in answers))
    for _, j in _judgments(run_dir):
        verdict = {r["id"]: r["verdict"] for r in j["judgments"]}
        lines += [
            f"## Judged by {j['judge_model']} @ {j['judge_digest'][:12]}",
            "",
            "Usable only if the kappa below says so. Accuracy given a hit is the headline;"
            " unconditioned is shown beside it, never instead.",
            "",
            "| stratum | accuracy given a hit (top 5) | unconditioned | not answered | unparsed |",
            "|---|---|---|---|---|",
        ]
        for s in strata:
            mine = [a for a in answers if a["stratum"] == s and a["id"] in verdict]
            hits = [a for a in mine if a["hit_rank"] is not None and a["hit_rank"] <= K]
            lines.append(
                f"| {s} | {_cell([verdict[a['id']] == 'correct' for a in hits])} | "
                f"{_cell([verdict[a['id']] == 'correct' for a in mine])} | "
                f"{sum(verdict[a['id']] == 'not_answered' for a in mine)} | "
                f"{sum(verdict[a['id']] == 'unparsed' for a in mine)} |"
            )
        lines += ["", *agreement_lines(verdict)]
    return lines


def agreement_lines(verdict: dict[str, str]) -> list[str]:
    """Kappa between the judge and the hand labels, where both exist."""
    hand = {i["id"]: i["verdict"] for i in _review_items() if i.get("verdict")}
    both = [i for i in hand if i in verdict and verdict[i] != "unparsed"]
    if not both:
        return ["No hand labels yet: `make answer-sample RUN=...`, label, then rerun the report.",
                ""]  # fmt: skip
    a3, b3 = [hand[i] for i in both], [verdict[i] for i in both]
    a2 = ["correct" if x == "correct" else "not" for x in a3]
    b2 = ["correct" if x == "correct" else "not" for x in b3]
    out = [f"### Judge against hand labels ({len(both)} answers)", ""]
    for name, a, b in (("correct vs not", a2, b2), ("three verdicts", a3, b3)):
        k = kappa(a, b)
        ci = bootstrap(a, b)
        if k is None:
            out.append(f"- {name}: kappa undefined (one label used for everything)")
            continue
        interval = f" [{ci[0]:.2f}, {ci[1]:.2f}]" if ci else ""
        out.append(f"- {name}: kappa {k:.2f}{interval} ({landis_koch(k)})")
    hand_rate = sum(x == "correct" for x in a3) / len(a3)
    judge_rate = sum(x == "correct" for x in b3) / len(b3)
    out += [
        f"- \"correct\" rate on these answers: hand {hand_rate:.0%}, judge {judge_rate:.0%}",
        "",
        "| hand \\ judge | correct | incorrect | not_answered |",
        "|---|---|---|---|",
        *[f"| {h} | " + " | ".join(str(sum(1 for x, y in zip(a3, b3, strict=True)
                                            if x == h and y == j))
                                  for j in ("correct", "incorrect", "not_answered")) + " |"
          for h in ("correct", "incorrect", "not_answered")],
        "",
    ]  # fmt: skip
    return out
