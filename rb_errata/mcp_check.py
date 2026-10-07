"""`make mcp-check`: the server, over stdio, against the committed snapshot.

It starts the server as a subprocess and speaks JSON-RPC over its pipes, as
Claude Desktop does, so the check covers the transport, the tool schemas and
the search, not just the functions behind them. Every question goes through
`search_rules` at its own as_of; the top 5 refs are compared with the snapshot
of the run the Results page reports as best, and graded by the same rule.

The report holds refs, counts and timings only, never rule text.
"""

from __future__ import annotations

import json
import statistics
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from rb_errata import recall
from rb_errata.labels import counterparts as counterparts_mod
from rb_errata.labels.review import load_questions

SNAPSHOT = Path("evals/runs/recall-as-of-qwen3-2026-10-04T1415Z")
K = 5


def _row(passages: list[dict[str, Any]]) -> dict[str, Any]:
    """A tool result in the snapshot's row shape, so recall.grade applies unchanged."""
    return {"ranked": [
        {"source_ref": p["ref"], "refs": [r.split(":", 1)[1] for r in p["rules"]],
         "valid_from": p["valid_from"], "valid_to": p["valid_to"]}
        for p in passages
    ]}  # fmt: skip


async def _check() -> list[str]:
    from mcp import Client
    from mcp.client.stdio import StdioServerParameters

    snap = {r["id"]: r for r in json.loads((SNAPSHOT / "retrieval.json").read_text())["results"]}
    questions = load_questions()
    cp = counterparts_mod.load()
    params = StdioServerParameters(
        command=sys.executable, args=["-m", "rb_errata.server"], cwd=str(Path.cwd())
    )
    timings: list[float] = []
    same, diffs, errors = 0, [], []
    fatal = ""
    hits: dict[str, list[bool]] = {}
    snap_hits: dict[str, list[bool]] = {}
    async with Client(params) as c:
        names = sorted(t.name for t in (await c.list_tools()).tools)
        for n, q in enumerate(questions, 1):
            if n == 1 or n % 40 == 0:
                print(f"  question {n}/{len(questions)}", file=sys.stderr, flush=True)
            args = {"question": q["question"], "as_of": str(q["as_of"]), "k": K}
            started = time.perf_counter()
            res = await c.call_tool("search_rules", args)
            timings.append(time.perf_counter() - started)
            if res.is_error:
                msg = res.content[0].text if res.content else "?"  # type: ignore[union-attr]
                if n == 1:
                    # Database or Ollama down: one clear line, not 224 copies of it.
                    # Raised after the session closes, outside the SDK's task group.
                    fatal = msg
                    break
                errors.append(f"{q['id']}: {msg}")
                continue
            passages = (res.structured_content or {})["passages"]
            got = [p["ref"] for p in passages]
            want = [r["source_ref"] for r in snap[q["id"]]["ranked"][:K]]
            if got == want:
                same += 1
            else:
                diffs.append(f"{q['id']}: server {got} / snapshot {want}")
            g = recall.grade(q, _row(passages), cp)
            s = recall.grade(q, snap[q["id"]], cp)
            hits.setdefault(q["stratum"], []).append(g["hit_rank"] is not None)
            snap_hits.setdefault(q["stratum"], []).append(
                s["hit_rank"] is not None and s["hit_rank"] <= K
            )
        # Cold, then warm: the first call for a version parses its PDF.
        ref = questions[0]["expect_sources"][0]
        version = ref.split("@", 1)[1].split(":", 1)[0]
        older = {"1.4": "1.3", "1.3": "1.2", "1.2": "1.1"}.get(version, "1.1")
        cold = []
        for name, a in (
            []
            if fatal
            else [
                ("get_rule", {"ref": ref}),
                ("get_rule", {"ref": ref}),
                ("what_changed", {"from_version": older, "to_version": version, "ref": ref}),
            ]
        ):
            started = time.perf_counter()
            res = await c.call_tool(name, a)
            cold.append((name, time.perf_counter() - started, res.is_error))

    if fatal:
        raise SystemExit(f"search_rules failed on the first question: {fatal}")
    warm = sorted(timings[1:])
    lines = [
        f"# MCP check against {SNAPSHOT.name}",
        "",
        f"Server over stdio (`python -m rb_errata.server`); tools: {', '.join(names)}.",
        f"Captured {datetime.now(UTC).strftime('%Y-%m-%dT%H%MZ')}.",
        "",
        f"## Parity: same top-{K} refs, same order",
        "",
        f"{same} of {len(questions)} identical; {len(diffs)} differ; {len(errors)} errors.",
        "",
        f"| stratum | recall@{K} via server | snapshot |",
        "|---|---|---|",
    ]
    for stratum in hits:
        lines.append(
            f"| {stratum} | {recall._cell(hits[stratum])} | {recall._cell(snap_hits[stratum])} |"
        )
    lines += [
        "",
        "## Timing (seconds, client side, includes the pipe)",
        "",
        f"search_rules: first call {timings[0]:.2f}; warm median "
        f"{statistics.median(warm):.3f}, p90 {warm[int(0.9 * (len(warm) - 1))]:.3f}.",
    ]
    for name, secs, err in cold:
        lines.append(f"- {name}: {secs:.2f}" + (" (error)" if err else ""))
    lines.append(
        f"(The calls above use {ref}; the first get_rule parses v{version}, what_changed "
        f"parses v{older}.)"
    )
    if diffs:
        lines += ["", "## Differences", "", *[f"- {d}" for d in diffs]]
    if errors:
        lines += ["", "## Errors", "", *[f"- {e}" for e in errors]]
    return lines


def run() -> Path:
    import anyio

    lines = anyio.run(_check)
    out = recall.RUNS / f"mcp-check-{datetime.now(UTC).strftime('%Y-%m-%dT%H%MZ')}"
    out.mkdir(parents=True, exist_ok=False)
    (out / "report.md").write_text("\n".join(lines) + "\n")
    return out
