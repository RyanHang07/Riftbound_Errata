"""Slice 14 contracts: the graph's paths, its spans, and the paired comparison."""

from __future__ import annotations

import json
from collections.abc import Iterator
from datetime import date
from pathlib import Path
from typing import Any

import pytest

from rb_errata.agent import evaluate, graph
from rb_errata.retrieve.vector import Passage

DAY = date(2026, 10, 1)
RULE = "A card that is Countered is not considered to have been played for abilities that trigger."


def passages(k: int) -> list[Passage]:
    return [Passage(f"core@1.4:{100 + i}", [f"{100 + i}"], RULE, 0.3 + i / 100, date(2026, 7, 24),
                    None, f"h{i}") for i in range(k)]  # fmt: skip


def deps(confs: list[float | None], route: str = '{"names_card": false}',
         answer: str = "No [core@1.4:100].") -> tuple[graph.Deps, list[int]]:  # fmt: skip
    ks: list[int] = []
    it: Iterator[float | None] = iter(confs)

    def gen(text: str, max_tokens: int, json_mode: bool = False) -> tuple[str, int, float]:
        return (route, 5, 0.1) if json_mode else (answer, 20, 1.0)

    def search(q: str, k: int, day: date) -> list[Passage]:
        ks.append(k)
        return passages(k)

    return graph.Deps(gen, search, lambda row, day: next(it), lambda day: []), ks


def test_confident_answer_is_not_re_searched() -> None:
    d, ks = deps([0.9])
    state, _ = graph.ask(graph.build(d), "q", DAY)
    assert ks == [5] and state["attempts"] == 0 and state["confidences"] == [0.9]


def test_low_confidence_re_searches_once_and_wider() -> None:
    d, ks = deps([0.1, 0.1])  # still low after the retry: it stops anyway
    state, _ = graph.ask(graph.build(d), "q", DAY)
    assert ks == [5, 10] and state["attempts"] == 1 and state["confidences"] == [0.1, 0.1]
    assert state["steps"][-1] == "finish"


def test_no_confidence_model_means_no_loop() -> None:
    d, ks = deps([None])
    state, _ = graph.ask(graph.build(d), "q", DAY)
    assert ks == [5] and state["confidence"] is None


def test_card_note_only_for_card_questions_and_unparsed_route_is_none() -> None:
    d, _ = deps([0.9], route='{"names_card": true}')
    assert graph.CARD_NOTE in graph.ask(graph.build(d), "q", DAY)[0]["answer"]
    d, _ = deps([0.9], route="maybe")
    state, _ = graph.ask(graph.build(d), "q", DAY)
    assert state["names_card"] is None and graph.CARD_NOTE not in state["answer"]


def test_agent_answers_pass_the_quote_guard() -> None:
    d, _ = deps([0.9], answer=f"No. {RULE}")
    assert (
        "[quoted text from core@1.4:100 removed]"
        in graph.ask(graph.build(d), "q", DAY)[0]["answer"]
    )


def test_generation_time_adds_up_over_calls() -> None:
    d, _ = deps([0.1, 0.9])
    state, _ = graph.ask(graph.build(d), "q", DAY)
    assert state["gen_s"] == pytest.approx(0.1 + 1.0 + 1.0)  # route + two answers


def test_every_node_is_a_span(monkeypatch: pytest.MonkeyPatch) -> None:
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

    from rb_errata.agent import tracing

    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    monkeypatch.setattr(tracing, "tracer", lambda: provider.get_tracer("test"))
    d, _ = deps([0.1, 0.9])
    graph.ask(graph.build(d), "q", DAY)
    names = [s.name for s in exporter.get_finished_spans()]
    assert names.count("retrieve") == 2 and names.count("answer") == 2 and names[-1] == "agent"
    kinds = {
        s.name: (s.attributes or {})["openinference.span.kind"]
        for s in exporter.get_finished_spans()
    }
    assert kinds["retrieve"] == "RETRIEVER" and kinds["answer"] == "LLM"


def _write(d: Path, rows: list[dict[str, Any]], verdicts: dict[str, str]) -> None:
    d.mkdir()
    (d / "answers.json").write_text(json.dumps({"answers": rows}))
    (d / "judgments-g.json").write_text(json.dumps(
        {"judgments": [{"id": k, "verdict": v} for k, v in verdicts.items()]}))  # fmt: skip


def test_compare_pairs_by_question_and_grades_the_router(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    qs = [{"id": "a", "stratum": "expert-ruling", "category": "cards"},
          {"id": "b", "stratum": "expert-ruling", "category": "mechanics"},
          {"id": "c", "stratum": "version-change"}]  # fmt: skip
    monkeypatch.setattr(evaluate, "load_questions", lambda: qs)
    base = [{"id": q["id"], "prompt_s": 1.0, "answer_s": 1.0} for q in qs]
    agent = [{"id": "a", "attempts": 1, "names_card": True, "gen_s": 4.0},
             {"id": "b", "attempts": 0, "names_card": True, "gen_s": 2.0},
             {"id": "c", "attempts": 1, "names_card": None, "gen_s": 4.0}]  # fmt: skip
    _write(tmp_path / "base", base, {"a": "incorrect", "b": "correct", "c": "correct"})
    _write(tmp_path / "agent", agent, {"a": "correct", "b": "correct", "c": "incorrect"})
    text = "\n".join(evaluate.compare(tmp_path / "base", tmp_path / "agent"))
    assert "| all | 2/3 = 67%" in text and "| 2/3 = 67%" in text and "| 1 | 1 |" in text
    assert "Re-search fired on 2/3" in text
    assert "Accuracy 1/2 = 50%" in text  # a right, b wrong; c has no category
    assert "(+67%)" in text  # 10 s against 6 s
