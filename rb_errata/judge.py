"""The LLM judge: does an answer reach the reference answer's conclusion? (slice 11)

A measuring instrument, so it is built to be checked, not trusted (brief
section 3): its labels are compared with the user's hand labels (Cohen's
kappa, rb_errata/labels/agreement.py) before any accuracy built on it is
reported as usable.

Three verdicts. `correct`: same conclusion as the reference. `incorrect`: a
different or contradicting conclusion. `not_answered`: no conclusion, or the
answer says the passages do not cover it. The judge grades the conclusion
only, not style or citations: citation correctness is what recall@k measures.

The judge sees the reference answer and the candidate answer, never the
retrieved passages, so it cannot be talked into agreeing by the same text
that misled the generator.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from rb_errata.config import Settings
from rb_errata.labels.review import load_questions

VERDICTS = ("correct", "incorrect", "not_answered")

TEMPLATE = """You are grading an answer to a question about the rules of the Riftbound \
trading card game. A rules expert wrote the reference answer; treat it as right.

Question: {question}

Reference answer:
{reference}

Answer to grade:
{answer}

Grade only whether the answer to grade reaches the same conclusion as the reference. \
Ignore style, length, extra detail and citations.
- "correct": it reaches the same conclusion.
- "incorrect": it reaches a different or contradicting conclusion.
- "not_answered": it gives no conclusion, or says the information is not available.

Reply with JSON only: {{"verdict": "correct" | "incorrect" | "not_answered", \
"reason": "one short sentence"}}"""

TEMPLATE_SHA256 = hashlib.sha256(TEMPLATE.encode()).hexdigest()


def reference(q: dict[str, Any]) -> str:
    """The reference answer the judge grades against.

    Rulings carry the expert's answer. Version-change questions carry the
    change note, which states the old and the new answer; the judge is told
    which side the question's date falls on, derived from its id.
    """
    if q.get("answer"):
        return str(q["answer"])
    side = "the CURRENT answer" if q["id"].endswith("-current") else "the OLD answer"
    return (
        f"{q['change']}\n\nThis question is dated {q['as_of']}, so the right answer is "
        f"{side} described above."
    )


def build(q: dict[str, Any], answer: str) -> str:
    return TEMPLATE.format(question=q["question"], reference=reference(q), answer=answer)


def parse(raw: str) -> tuple[str, str]:
    """(verdict, reason) from the judge's reply; ("unparsed", text) if malformed. Pure.

    Unparsed is its own outcome, counted and shown, never mapped to a verdict:
    guessing the judge's intent would be the judge's error plus ours.
    """
    try:
        data = json.loads(raw)
        verdict = str(data["verdict"]).strip().lower().replace(" ", "_")
    except (json.JSONDecodeError, KeyError, TypeError):
        m = re.search(r'"verdict"\s*:\s*"([a-z_ ]+)"', raw)
        if m is None:
            return "unparsed", raw.strip()[:200]
        verdict, data = m.group(1).replace(" ", "_"), {}
    if verdict not in VERDICTS:
        return "unparsed", raw.strip()[:200]
    return verdict, str(data.get("reason", "")) if isinstance(data, dict) else ""


def slug(tag: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", tag.lower()).strip("-")


def run(settings: Settings, run_dir: Path) -> Path:
    from rb_errata.ollama import Ollama, checked_digest

    snap = json.loads((run_dir / "answers.json").read_text())
    questions = {q["id"]: q for q in load_questions()}
    tag, pinned = settings.judge
    client = Ollama(settings)
    out_rows = []
    try:
        digest = checked_digest(client, tag, pinned)
        started = time.perf_counter()
        placement = None
        for n, a in enumerate(snap["answers"], 1):
            if n == 1 or n % 40 == 0:
                print(f"  judging {n}/{len(snap['answers'])}", file=sys.stderr, flush=True)
            q = questions.get(a["id"])
            if q is None:  # relabelled since the answers were generated (A44)
                continue
            g = client.generate(
                build(q, a["answer"]), max_tokens=settings.judge_max_tokens, model=tag,
                json_mode=True,
            )  # fmt: skip
            if placement is None:
                placement = client.loaded_vram_fraction(tag)
            verdict, reason = parse(g.text)
            out_rows.append({"id": a["id"], "verdict": verdict, "reason": reason})
        elapsed = time.perf_counter() - started
    finally:
        client.close()
    out = run_dir / f"judgments-{slug(tag)}.json"
    out.write_text(json.dumps({
        "captured_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "judge_model": tag,
        "judge_digest": digest,
        "template_sha256": TEMPLATE_SHA256,
        "gpu_fraction": placement,
        "cpu_only": settings.cpu_only,
        "seconds": round(elapsed, 1),
        "judgments": out_rows,
    }, indent=1) + "\n")  # fmt: skip
    return out
