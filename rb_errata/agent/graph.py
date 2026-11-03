"""Slice 14: the agent as a LangGraph graph.

    START -> route -> retrieve -> answer -> check --(confident, or tried twice)--> finish -> END
                         ^                    |
                         +---- re_search <----+  (confidence below THRESHOLD, first try only)

- route: does the question name a specific card? Asked of the generator,
  JSON-constrained. Card questions get a note in the answer: card text is
  not in the corpus (slice 12: card questions are 23 of the 25 misses outside
  the top 20). The router is graded against each ruling's source category.
- retrieve: the measured best (as-of), k = 5, then k = 10 on a re-search.
  Wider, not reworded: slice 12 found 26 of 47 below-cutoff misses at rank 6
  to 10, which is exactly what a wider k reaches.
- answer: the committed prompt and generator, quote guard applied.
- check: freshness warnings (slice 18) and slice 13's confidence score.

Dependencies are injected (Deps), so the graph's logic is tested with fakes
and the real wiring (Deps.live) stays thin. Every node is a span (tracing.py).
"""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from rb_errata.agent.tracing import KIND, span
from rb_errata.generate import prompt
from rb_errata.generate.quotes import redact
from rb_errata.retrieve.vector import Passage

THRESHOLD = 0.5
K_FIRST, K_RETRY = 5, 10
CARD_NOTE = (
    "Note: this question names a card, and card text is not in this tool's corpus yet, "
    "so the answer rests on the Core Rules alone."
)
ROUTE_PROMPT = """Does this question about the Riftbound trading card game name a specific \
card by its proper name (for example "Abandoned Hall" or "Ravenbloom Student"), rather than \
asking only about general rules, keywords or game terms?

Question: {question}

Reply with JSON only: {{"names_card": true}} or {{"names_card": false}}"""


class State(TypedDict, total=False):
    question: str
    as_of: str
    names_card: bool | None
    passages: list[Passage]
    answer: str
    quotes_removed: int
    confidence: float | None
    confidences: list[float | None]
    warnings: list[str]
    attempts: int
    k: int
    steps: list[str]
    answer_tokens: int
    gen_s: float  # Ollama's own prefill + decode seconds, summed over every call


@dataclass
class Deps:
    # (prompt, max_tokens=, json_mode=) -> (text, answer tokens, Ollama seconds)
    generate: Callable[..., tuple[str, int, float]]
    search: Callable[[str, int, date], list[Passage]]
    confidence: Callable[[dict[str, Any], date], float | None]
    freshness: Callable[[date], list[str]]
    max_tokens: int = 400

    @classmethod
    def live(cls, settings: Any, client: Any, model: dict[str, Any] | None) -> Deps:
        """The real wiring: Ollama, Postgres, the saved confidence model."""
        from rb_errata import confidence as conf
        from rb_errata import tools
        from rb_errata.retrieve.methods import retrieve

        windows = {v: (w.valid_from, w.valid_to) for v, w in tools.windows().items()}

        def gen(text: str, max_tokens: int, json_mode: bool = False) -> tuple[str, int, float]:
            g = client.generate(text, max_tokens=max_tokens, json_mode=json_mode)
            return g.text, g.answer_tokens, (g.prompt_ns + g.answer_ns) / 1e9

        def search(q: str, k: int, day: date) -> list[Passage]:
            return retrieve("as-of", settings, client, q, k, day)

        def score(row: dict[str, Any], day: date) -> float | None:
            return None if model is None else conf.score(model, conf.signals(row, day, windows))

        return cls(gen, search, score, tools.freshness, settings.gen_max_tokens)


def row_of(state: State, answer_tokens: int) -> dict[str, Any]:
    """The state as an answers.json row, so slice 13's signals apply unchanged."""
    ps = state.get("passages", [])
    return {
        "answer": state.get("answer", ""),
        "retrieved": [p.source_ref for p in ps],
        "distances": [p.distance for p in ps],
        "retrieved_refs": sorted(set().union(*(p.qualified_refs for p in ps))) if ps else [],
        "answer_tokens": answer_tokens,
    }


def build(deps: Deps) -> Any:
    def route(state: State) -> State:
        with span("route", KIND.LLM, **{"input.value": state["question"]}) as s:
            raw, _, secs = deps.generate(
                ROUTE_PROMPT.format(question=state["question"]), max_tokens=20, json_mode=True
            )
            try:
                names_card: bool | None = bool(json.loads(raw)["names_card"])
            except (json.JSONDecodeError, KeyError, TypeError):
                names_card = None  # unparsed: counted, never guessed
            s.set_attribute("output.value", str(names_card))
        return {"names_card": names_card, "attempts": 0, "k": K_FIRST, "confidences": [],
                "steps": ["route"], "gen_s": secs}  # fmt: skip

    def retrieve(state: State) -> State:
        day = date.fromisoformat(state["as_of"])
        with span("retrieve", KIND.RETRIEVER, **{"input.value": state["question"],
                                                 "rb.k": state["k"]}) as s:  # fmt: skip
            passages = deps.search(state["question"], state["k"], day)
            s.set_attribute("output.value", ", ".join(p.source_ref for p in passages))
        return {"passages": passages, "steps": [*state["steps"], f"retrieve k={state['k']}"]}

    def answer(state: State) -> State:
        text = prompt.build(state["question"], state["passages"])
        with span("answer", KIND.LLM, **{"input.value": state["question"]}) as s:
            raw, tokens, secs = deps.generate(text, max_tokens=deps.max_tokens)
            out, quoted = redact(raw.strip(), [(p.source_ref, p.text) for p in state["passages"]])
            s.set_attribute("output.value", out)
        return {"answer": out, "quotes_removed": quoted, "answer_tokens": tokens,
                "gen_s": state["gen_s"] + secs, "steps": [*state["steps"], "answer"]}  # fmt: skip

    def check(state: State) -> State:
        day = date.fromisoformat(state["as_of"])
        with span("check", KIND.CHAIN) as s:
            conf = deps.confidence(row_of(state, state["answer_tokens"]), day)
            warnings = deps.freshness(day)
            if conf is not None:
                s.set_attribute("rb.confidence", conf)
            s.set_attribute("rb.warnings", len(warnings))
        return {"confidence": conf, "confidences": [*state["confidences"], conf],
                "warnings": warnings, "steps": [*state["steps"], "check"]}  # fmt: skip

    def re_search(state: State) -> State:
        return {"attempts": state["attempts"] + 1, "k": K_RETRY,
                "steps": [*state["steps"], "re_search"]}  # fmt: skip

    def finish(state: State) -> State:
        note = state.get("answer", "")
        if state.get("names_card"):
            note = f"{note}\n\n{CARD_NOTE}"
        return {"answer": note, "steps": [*state["steps"], "finish"]}

    def after_check(state: State) -> str:
        c = state.get("confidence")
        if c is not None and c < THRESHOLD and state["attempts"] == 0:
            return "re_search"
        return "finish"

    g = StateGraph(State)
    for name, fn in (("route", route), ("retrieve", retrieve), ("answer", answer),
                     ("check", check), ("re_search", re_search), ("finish", finish)):  # fmt: skip
        g.add_node(name, fn)
    g.add_edge(START, "route")
    g.add_edge("route", "retrieve")
    g.add_edge("retrieve", "answer")
    g.add_edge("answer", "check")
    g.add_conditional_edges("check", after_check, {"re_search": "re_search", "finish": "finish"})
    g.add_edge("re_search", "retrieve")
    g.add_edge("finish", END)
    return g.compile()


def ask(graph: Any, question: str, as_of: date) -> tuple[State, float]:
    """Run the graph for one question under a root span; (final state, seconds)."""
    started = time.perf_counter()
    with span("agent", KIND.AGENT, **{"input.value": question, "rb.as_of": as_of.isoformat()}):
        state: State = graph.invoke({"question": question, "as_of": as_of.isoformat()})
    return state, time.perf_counter() - started
