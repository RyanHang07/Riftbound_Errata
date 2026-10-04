"""Slice 5 contracts: the hit rule, three states, and the outdated-copy column."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from rb_errata import recall
from rb_errata.ingest.rules import Rule
from rb_errata.labels import counterparts as counterparts_mod
from rb_errata.labels.counterparts import counterparts

V13 = {"valid_from": "2026-03-30", "valid_to": "2026-07-24"}
V14 = {"valid_from": "2026-07-24", "valid_to": None}


def chunk(doc: str, refs: list[str], window: dict[str, Any]) -> dict[str, Any]:
    return {"source_ref": f"{doc}:{refs[0]}", "refs": refs, **window}


Q = {"id": "q", "stratum": "s", "as_of": "2026-10-01", "expect_sources": ["core@1.4:419.4.a"]}
CP = {"core@1.4:419.4.a": [{"ref": "core@1.3:419.4.a", "same_text": False}]}


def test_hit_needs_right_ref_and_version() -> None:
    # The outdated copy carries the same number but is not in effect on as_of:
    # by A1 it is not a hit, it is the outdated copy, ranked above the hit.
    row = {"id": "q", "ranked": [
        chunk("core@1.3", ["419", "419.4.a"], V13),
        chunk("core@1.4", ["300.1"], V14),
        chunk("core@1.4", ["419", "419.4.a"], V14),
    ]}  # fmt: skip
    g = recall.grade(Q, row, CP)
    assert (g["hit_rank"], g["outdated_rank"], g["blind_rank"]) == (3, 1, 1)


def test_same_text_copy_is_not_outdated() -> None:
    # A copy with identical text in another version cannot mislead a reader;
    # it counts for version-blind recall only.
    cp = {"core@1.4:419.4.a": [{"ref": "core@1.3:419.4.a", "same_text": True}]}
    row = {"id": "q", "ranked": [chunk("core@1.3", ["419.4.a"], V13)]}
    g = recall.grade(Q, row, cp)
    assert (g["hit_rank"], g["outdated_rank"], g["blind_rank"]) == (None, None, 1)


def test_errored_search_is_unknown_not_a_miss() -> None:
    assert recall.grade(Q, {"id": "q", "error": "boom"}, CP)["state"] == "unknown"


def test_report_excludes_unknown_from_denominator(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    q2 = {**Q, "id": "q2"}
    monkeypatch.setattr(recall, "load_questions", lambda: [Q, q2])
    monkeypatch.setattr(counterparts_mod, "load", lambda: CP)
    snap = {
        "retrieval": {"method": "m", "embed_model": "e", "embed_digest": "d" * 12},
        "corpus_chunks_sha256": "c" * 12, "questions_sha256": "q" * 12,
        "results": [
            {"id": "q", "ranked": [chunk("core@1.4", ["419.4.a"], V14)]},
            {"id": "q2", "error": "timeout"},
        ],
    }  # fmt: skip
    (tmp_path / "retrieval.json").write_text(json.dumps(snap))
    text = "\n".join(recall.report(tmp_path))
    assert "| s | 1/1 = 100%" in text and "| 1 |" in text


def test_counterparts_align_by_text_not_number() -> None:
    # Renumbered between versions (A15): the copy of 1.4's 419.4.a is 1.3's
    # 406.4.a. A number join would pair it with 1.3's unrelated 419.4.a.
    text = "A spell that is countered is not considered played for triggered abilities"
    v13 = [
        Rule("406.4.a", text),
        Rule("419.4.a", "Each player draws two cards at the start of the turn"),
    ]
    v14 = [Rule("419.4.a", text + " unless it was finalized")]
    cp = counterparts({"1.3": v13, "1.4": v14}, {"core@1.4:419.4.a"})
    assert cp == {"core@1.4:419.4.a": [{"ref": "core@1.3:406.4.a", "same_text": False}]}


def test_sql_and_python_agree_on_in_effect() -> None:
    # Two definitions of "in effect" exist: the SQL predicate that filters
    # before ranking, and Passage.in_effect_on used to grade. They must agree
    # on the boundary days, where a version hands over to the next.
    from datetime import date

    from rb_errata.retrieve.vector import IN_EFFECT, Passage

    def sql(day: date, start: date, end: date | None) -> bool:
        # Evaluate the predicate's text as Python on the same values.
        expr = IN_EFFECT.replace("%(as_of)s", "day").replace("AND", "and").replace("OR", "or")
        expr = expr.replace("valid_to IS NULL", "end is None").replace("valid_from", "start")
        return bool(
            eval(expr.replace("valid_to", "end"), {}, {"day": day, "start": start, "end": end})
        )

    start, end = date(2026, 3, 30), date(2026, 7, 24)
    for day in (date(2026, 3, 29), start, date(2026, 7, 23), end):
        for e in (end, None):
            p = Passage("core@1.3:1", ["1"], "", 0.0, start, e, "h")
            assert sql(day, start, e) == p.in_effect_on(day), (day, e)


def test_compare_refuses_runs_on_different_questions(tmp_path: Path) -> None:
    for name, qhash in (("a", "x"), ("b", "y")):
        (tmp_path / name).mkdir()
        snap = {"questions_sha256": qhash, "corpus_chunks_sha256": "c", "results": []}
        (tmp_path / name / "retrieval.json").write_text(json.dumps(snap))
    with pytest.raises(SystemExit):
        recall.compare(tmp_path / "a", tmp_path / "b")


def test_mcnemar_p_exact() -> None:
    from rb_errata.labels.power import mcnemar_p

    # 6 of 6 discordant one way: 2 * 0.5**6 = 0.03125.
    assert mcnemar_p(6, 6) == pytest.approx(0.03125)
    assert mcnemar_p(0, 0) == 1.0


def _p(ref: str) -> Any:
    from datetime import date

    from rb_errata.retrieve.vector import Passage

    return Passage(ref, [ref], "", 0.0, date(2026, 7, 24), None, "h-" + ref)


def test_rrf_rewards_agreement_between_lists() -> None:
    # "b" is second in both lists; "a" is first in one and absent from the
    # other. Agreement wins: 2/62 > 1/61.
    from rb_errata.retrieve.methods import rrf

    fused = rrf([[_p("a"), _p("b")], [_p("c"), _p("b")]], k=3)
    assert [p.source_ref for p in fused] == ["b", "a", "c"]


def test_rrf_with_an_empty_list_keeps_the_other_order() -> None:
    # A question of only stopwords gives no full-text results; the hybrid
    # must then be exactly the vector ranking, not a reshuffle.
    from rb_errata.retrieve.methods import rrf

    fused = rrf([[_p("a"), _p("b"), _p("c")], []], k=3)
    assert [p.source_ref for p in fused] == ["a", "b", "c"]


def test_every_method_is_dispatchable() -> None:
    import inspect

    from rb_errata.retrieve import methods

    src = inspect.getsource(methods.retrieve)
    assert all(f'"{m}"' in src for m in methods.METHODS)
