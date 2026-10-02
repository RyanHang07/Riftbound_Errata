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
