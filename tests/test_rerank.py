"""Slice 9 contracts: pooling, ordering, and the weights pin. No model download."""

from __future__ import annotations

import dataclasses
from datetime import date
from pathlib import Path

import pytest

from rb_errata import config
from rb_errata.retrieve import rerank
from rb_errata.retrieve.vector import Passage


def p(ref: str, h: str = "") -> Passage:
    return Passage(ref, [ref], f"text {ref}", 0.0, date(2026, 7, 24), None, h or "h-" + ref)


def test_pool_deduplicates_across_lists() -> None:
    # A chunk found by both vector and full-text search is one candidate, not
    # two: duplicates would take two of the five answer slots.
    pooled = rerank.pool([[p("a"), p("b")], [p("b"), p("c")]])
    assert [x.source_ref for x in pooled] == ["a", "b", "c"]


def test_order_is_by_score_with_stable_ties() -> None:
    out = rerank.order([p("a"), p("b"), p("c")], [0.1, 0.9, 0.1], k=3)
    assert [x.source_ref for x in out] == ["b", "a", "c"]
    assert out[0].distance == -0.9  # lower is better, as for vectors


def _fake_weights(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> config.Settings:
    snap = tmp_path / "models--BAAI--bge-reranker-base" / "snapshots" / "abc123" / "onnx"
    snap.mkdir(parents=True)
    (snap / "model.onnx").write_bytes(b"weights")
    monkeypatch.setattr(rerank, "_ENCODERS", {"BAAI/bge-reranker-base": object()})
    monkeypatch.setattr(rerank, "_VERIFIED", {})
    return dataclasses.replace(config.load({}), rerank_cache_dir=str(tmp_path))


def test_unpinned_weights_refuse_and_print_the_hash(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    s = dataclasses.replace(_fake_weights(tmp_path, monkeypatch), rerank_sha256="")
    with pytest.raises(rerank.RerankPinError) as e:
        rerank.load(s)
    assert rerank.sha256_file(next(tmp_path.rglob("model.onnx"))) in str(e.value)


def test_changed_weights_refuse(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    s = dataclasses.replace(_fake_weights(tmp_path, monkeypatch), rerank_sha256="0" * 64)
    with pytest.raises(rerank.RerankPinError, match="weights changed"):
        rerank.load(s)


def test_pinned_weights_load(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    s = _fake_weights(tmp_path, monkeypatch)
    good = rerank.sha256_file(next(tmp_path.rglob("model.onnx")))
    ident = rerank.load(dataclasses.replace(s, rerank_sha256=good))
    assert ident == {"model": "BAAI/bge-reranker-base", "sha256": good, "snapshot": "abc123"}
