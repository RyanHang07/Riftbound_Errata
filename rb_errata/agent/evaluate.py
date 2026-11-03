"""Slice 14: run the agent over the question set, and compare it with slice 11.

`make agent-run CONF=.../confidence.json` writes an answers.json in slice
11's format (so `make judge` and `make answers-report` work on it unchanged)
plus the agent's own fields: route, confidences, attempts, final k, steps.

`make agent-compare A=<answers run> B=<agent run>` pairs the two by question
on their judge verdicts (exact McNemar), grades the router against each
ruling's source category, and reports how often the loop fired, what it
gained and lost, and Ollama's own generation time for both.
"""

from __future__ import annotations

import hashlib
import json
import statistics
import sys
from datetime import UTC, date, datetime
from pathlib import Path

from rb_errata import db, recall
from rb_errata.agent import graph as agent_graph
from rb_errata.agent.tracing import flush
from rb_errata.config import Settings
from rb_errata.generate import prompt
from rb_errata.labels import counterparts as counterparts_mod
from rb_errata.labels.power import mcnemar_p, wilson
from rb_errata.labels.review import load_questions


def run(settings: Settings, confidence_path: Path | None, limit: int | None = None) -> Path:
    from rb_errata.answers import _row
    from rb_errata.ollama import Ollama, checked_digest

    model = json.loads(confidence_path.read_text()) if confidence_path else None
    client = Ollama(settings)
    gen_digest = checked_digest(client, settings.gen_model, settings.gen_digest)
    checked_digest(client, settings.embed_model, settings.embed_digest)
    db.init(settings)
    if recall._db_corpus(settings) != recall._manifest_corpus():
        raise SystemExit("database differs from data/corpus.json; run `make ingest` first")
    stamp = datetime.now(UTC).strftime("%Y-%m-%dT%H%MZ")
    out_dir = recall.RUNS / f"agent-{settings.embed_profile}-{stamp}"
    if out_dir.exists():
        raise SystemExit(f"{out_dir} already exists; wait a minute and rerun")
    graph = agent_graph.build(agent_graph.Deps.live(settings, client, model))
    questions = load_questions()[:limit] if limit else load_questions()
    cp = counterparts_mod.load()
    rows, placement = [], None
    try:
        for n, q in enumerate(questions, 1):
            if n == 1 or n % 20 == 0:
                print(f"  agent {n}/{len(questions)}", file=sys.stderr, flush=True)
            day = date.fromisoformat(str(q["as_of"]))
            state, wall = agent_graph.ask(graph, q["question"], day)
            if placement is None:
                placement = client.loaded_vram_fraction(settings.gen_model)
            ps = state["passages"]
            rows.append({
                "id": q["id"],
                "stratum": q["stratum"],
                "retrieved": [p.source_ref for p in ps],
                "distances": [round(p.distance, 4) for p in ps],
                "retrieved_refs": sorted(set().union(*(p.qualified_refs for p in ps))),
                "hit_rank": recall.grade(q, _row(ps), cp)["hit_rank"],
                "names_card": state.get("names_card"),
                "attempts": state["attempts"],
                "k_final": state["k"],
                "confidences": state["confidences"],
                "warnings": state.get("warnings", []),
                "steps": state["steps"],
                "gen_s": round(state["gen_s"], 3),
                "wall_s": round(wall, 3),
                # Slice 11's report reads these; the agent's figures fill them.
                "prompt_s": round(state["gen_s"], 3),
                "answer_s": 0.0,
                "answer_tokens": state["answer_tokens"],
                "done_reason": "",
                "quotes_removed": state["quotes_removed"],
                "answer": state["answer"],
            })  # fmt: skip
    finally:
        client.close()
        flush()
    out_dir.mkdir(parents=True)
    (out_dir / "answers.json").write_text(json.dumps({
        "captured_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "agent": {"threshold": agent_graph.THRESHOLD, "k": [agent_graph.K_FIRST,
                  agent_graph.K_RETRY], "confidence_model": str(confidence_path) if model
                  else None},
        "generator": {"model": settings.gen_model, "digest": gen_digest,
                      "think": settings.gen_think, "temperature": settings.gen_temperature,
                      "seed": settings.gen_seed, "num_ctx": settings.gen_num_ctx,
                      "max_tokens": settings.gen_max_tokens},
        "template_sha256": prompt.TEMPLATE_SHA256,
        "retrieval": {"method": "as-of", "k": agent_graph.K_FIRST},
        "placement": {"gpu_fraction": placement, "cpu_only": settings.cpu_only},
        "corpus_chunks_sha256": json.loads(recall.CORPUS.read_text())["chunks_sha256"],
        "questions_sha256": hashlib.sha256(
            Path("evals/questions.yaml").read_bytes()).hexdigest(),
        "answers": rows,
    }, indent=1) + "\n")  # fmt: skip
    return out_dir


def _verdicts(run_dir: Path, judge: str | None) -> dict[str, str]:
    files = sorted(run_dir.glob(f"judgments-{judge or '*'}.json"))
    if len(files) != 1:
        raise SystemExit(f"need exactly one judgments file in {run_dir} (or pass JUDGE=)")
    return {r["id"]: r["verdict"] for r in json.loads(files[0].read_text())["judgments"]}


def _cell(k: int, n: int) -> str:
    if not n:
        return "n/a"
    lo, hi = wilson(k, n)
    return f"{k}/{n} = {k / n:.0%} [{lo:.0%}, {hi:.0%}]"


def compare(base_dir: Path, agent_dir: Path, judge: str | None = None) -> list[str]:
    base = {a["id"]: a for a in json.loads((base_dir / "answers.json").read_text())["answers"]}
    agent = {a["id"]: a for a in json.loads((agent_dir / "answers.json").read_text())["answers"]}
    vb, va = _verdicts(base_dir, judge), _verdicts(agent_dir, judge)
    questions = {q["id"]: q for q in load_questions()}
    judged = {i for i in vb if vb[i] != "unparsed"} & {i for i in va if va[i] != "unparsed"}
    ids = [i for i in agent if i in base and i in questions and i in judged]
    lines = [
        f"# Agent {agent_dir.name} against {base_dir.name}",
        "",
        "Paired by question on judge verdicts (correct vs not); exact two-sided McNemar.",
        "",
        "| questions | without loop | with loop | gained | lost | McNemar p |",
        "|---|---|---|---|---|---|",
    ]
    groups = [("all", ids)] + [
        (s, [i for i in ids if questions[i]["stratum"] == s])
        for s in dict.fromkeys(questions[i]["stratum"] for i in ids)
    ]
    groups.append(("re-searched only", [i for i in ids if agent[i]["attempts"] > 0]))
    for name, members in groups:
        a = [vb[i] == "correct" for i in members]
        b = [va[i] == "correct" for i in members]
        gained = sum(1 for x, y in zip(a, b, strict=True) if y and not x)
        lost = sum(1 for x, y in zip(a, b, strict=True) if x and not y)
        p = f"{mcnemar_p(gained, gained + lost):.3g}" if gained + lost else "n/a"
        lines.append(f"| {name} | {_cell(sum(a), len(a))} | {_cell(sum(b), len(b))} | "
                     f"{gained} | {lost} | {p} |")  # fmt: skip
    fired = [i for i in agent if agent[i]["attempts"] > 0]
    lines += ["", f"Re-search fired on {_cell(len(fired), len(agent))} of questions."]

    rulings = [i for i in agent if questions.get(i, {}).get("category")]
    routed = [i for i in rulings if agent[i]["names_card"] is not None]
    right = sum(agent[i]["names_card"] == (questions[i]["category"] == "cards") for i in routed)
    misses = [
        i for i in routed if questions[i]["category"] == "cards" and not agent[i]["names_card"]
    ]
    lines += [
        "",
        "## Router (names a specific card?) against each ruling's source category",
        "",
        f"Accuracy {_cell(right, len(routed))}; unparsed {len(rulings) - len(routed)}; card "
        f"questions routed as rules-only: {len(misses)}.",
    ]
    gb = [base[i]["prompt_s"] + base[i]["answer_s"] for i in ids]
    ga = [agent[i]["gen_s"] for i in ids]
    if gb and ga:
        lines += [
            "",
            "## Generation time (Ollama's own clock, prefill + decode)",
            "",
            f"Without loop: total {sum(gb):.0f} s, median {statistics.median(gb):.2f} s. With "
            f"loop (route call on every question, second answer when re-searched): total "
            f"{sum(ga):.0f} s, median {statistics.median(ga):.2f} s "
            f"({sum(ga) / sum(gb) - 1:+.0%}).",
        ]
    return lines
