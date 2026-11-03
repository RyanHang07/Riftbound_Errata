"""Is identical input identical output? (A54's follow-up)

The same prompts generated three times on the GPU and three times on the CPU
(Ollama's num_gpu = 0), at the committed settings (temperature 0, seed 42).
Only hashes and lengths of the answers are written: they can quote rules.
"""

from __future__ import annotations

import hashlib
import json
import random
import sys
from dataclasses import replace
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from rb_errata import recall
from rb_errata.config import Settings
from rb_errata.generate import prompt
from rb_errata.labels.review import load_questions

SEED = 20261103
N_PROMPTS = 10
REPEATS = 3


def identical(runs: list[list[str]]) -> int:
    """How many prompts gave the same hash on every repeat. Pure."""
    return sum(1 for hashes in runs if len(set(hashes)) == 1)


def run(settings: Settings) -> Path:
    from rb_errata.ollama import Ollama, checked_digest
    from rb_errata.retrieve.methods import retrieve

    questions = load_questions()
    picked = random.Random(SEED).sample(sorted(q["id"] for q in questions), N_PROMPTS)
    by_id = {q["id"]: q for q in questions}
    client = Ollama(settings)
    digest = checked_digest(client, settings.gen_model, settings.gen_digest)
    prompts = []
    for qid in sorted(picked):
        q = by_id[qid]
        ps = retrieve("as-of", settings, client, q["question"], recall.PROMPT_K,
                      date.fromisoformat(str(q["as_of"])))  # fmt: skip
        prompts.append((qid, prompt.build(q["question"], ps)))
    client.close()
    results: dict[str, Any] = {}
    for placement, cpu in (("gpu", False), ("cpu", True)):
        c = Ollama(replace(settings, cpu_only=cpu))
        rows = []
        try:
            for i, (qid, text) in enumerate(prompts, 1):
                print(f"  {placement} prompt {i}/{len(prompts)}", file=sys.stderr, flush=True)
                outs = [c.generate(text, max_tokens=settings.gen_max_tokens).text
                        for _ in range(REPEATS)]  # fmt: skip
                rows.append({"id": qid,
                             "sha256": [hashlib.sha256(o.encode()).hexdigest()[:16] for o in outs],
                             "chars": [len(o) for o in outs]})  # fmt: skip
            share = c.loaded_vram_fraction(settings.gen_model)
        finally:
            c.close()
        results[placement] = {"gpu_fraction": share, "prompts": rows}
    out = recall.RUNS / f"determinism-{datetime.now(UTC).strftime('%Y-%m-%dT%H%MZ')}"
    out.mkdir(parents=True, exist_ok=False)
    (out / "determinism.json").write_text(json.dumps({
        "generator": {"model": settings.gen_model, "digest": digest,
                      "temperature": settings.gen_temperature, "seed": settings.gen_seed},
        "repeats": REPEATS, **results}, indent=1) + "\n")  # fmt: skip
    lines = [
        f"# Determinism {out.name}",
        "",
        f"{N_PROMPTS} prompts x {REPEATS} repeats, temperature {settings.gen_temperature}, "
        f"seed {settings.gen_seed}.",
        "",
        "| placement | GPU share | prompts identical on every repeat |",
        "|---|---|---|",
    ]
    for placement, r in results.items():
        same = identical([row["sha256"] for row in r["prompts"]])
        held = "n/a" if r["gpu_fraction"] is None else f"{r['gpu_fraction']:.0%}"
        lines.append(f"| {placement} | {held} | {same} of {N_PROMPTS} |")
    (out / "report.md").write_text("\n".join(lines) + "\n")
    return out
