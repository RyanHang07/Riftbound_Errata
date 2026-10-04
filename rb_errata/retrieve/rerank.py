"""Cross-encoder reranking over a pooled candidate set (slice 9, A31).

A31 found full-text search a good candidate source and a bad ranker: the
right rule is in the union of the vector and full-text top 20 for 91% of
rulings and 96% of version-change questions, but rank fusion lost 8
version-change questions. So the two lists only supply candidates here, and
a cross-encoder, which reads question and passage together, orders them.

CPU only, on purpose (A8): the brief's target machine has no GPU, so every
latency figure here is measured where the tool will run.
"""

from __future__ import annotations

import hashlib
import time
from pathlib import Path
from typing import Any

from rb_errata.config import Settings
from rb_errata.retrieve.vector import Passage

_ENCODERS: dict[str, Any] = {}
# Verified once per process: hashing 1 GB of weights per question would cost
# more than the reranking it guards.
_VERIFIED: dict[str, dict[str, str]] = {}


class RerankPinError(SystemExit):
    pass


def _weights(settings: Settings) -> Path:
    # fastembed stores the Hugging Face snapshot under cache_dir in the hub
    # layout: models--<org>--<name>/snapshots/<commit>/onnx/model.onnx.
    folder = "models--" + settings.rerank_model.replace("/", "--")
    found = sorted(Path(settings.rerank_cache_dir).glob(f"{folder}/snapshots/*/onnx/model.onnx"))
    if len(found) != 1:
        raise RerankPinError(
            f"expected one weights file for {settings.rerank_model}, found {found}"
        )
    return found[0]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def load(settings: Settings) -> dict[str, str]:
    """Download if needed, verify the pin, keep the encoder. Returns its identity."""
    from fastembed.rerank.cross_encoder import TextCrossEncoder

    if settings.rerank_model in _VERIFIED:
        return _VERIFIED[settings.rerank_model]
    if settings.rerank_model not in _ENCODERS:
        _ENCODERS[settings.rerank_model] = TextCrossEncoder(
            settings.rerank_model,
            cache_dir=settings.rerank_cache_dir,
            providers=["CPUExecutionProvider"],
        )
    path = _weights(settings)
    observed = sha256_file(path)
    if not settings.rerank_sha256:
        raise RerankPinError(
            f"{settings.rerank_model} is unpinned. Observed weights SHA-256: {observed} "
            f"(snapshot {path.parent.parent.name}). If this is the model you intend, set "
            "rerank_sha256 in rb_errata/config.py to it."
        )
    if observed != settings.rerank_sha256:
        raise RerankPinError(
            f"{settings.rerank_model} weights changed: pinned {settings.rerank_sha256[:12]}, "
            f"found {observed[:12]}. Refusing: a different model is a different experiment."
        )
    ident = {
        "model": settings.rerank_model,
        "sha256": observed,
        "snapshot": path.parent.parent.name,
    }
    _VERIFIED[settings.rerank_model] = ident
    return ident


def pool(lists: list[list[Passage]]) -> list[Passage]:
    """Union of candidate lists, first occurrence kept, order irrelevant. Pure."""
    seen: set[tuple[str, str]] = set()
    out = []
    for ranked in lists:
        for p in ranked:
            key = (p.source_ref, p.content_hash)
            if key not in seen:
                seen.add(key)
                out.append(p)
    return out


def order(candidates: list[Passage], scores: list[float], k: int) -> list[Passage]:
    """Top k by cross-encoder score, highest first. Pure; unit-tested.

    Ties keep candidate order, so the result is deterministic. distance is
    the negated score: lower is better everywhere in this codebase.
    """
    ranked = sorted(range(len(candidates)), key=lambda i: (-scores[i], i))[:k]
    return [
        Passage(c.source_ref, c.refs, c.text, -scores[i], c.valid_from, c.valid_to, c.content_hash)
        for i in ranked
        for c in [candidates[i]]
    ]


def rerank(
    settings: Settings, query: str, candidates: list[Passage], k: int
) -> tuple[list[Passage], float]:
    """Rerank and return (top k, seconds spent in the cross-encoder)."""
    load(settings)
    t0 = time.perf_counter()
    scores = [
        float(s)
        for s in _ENCODERS[settings.rerank_model].rerank(query, [c.text for c in candidates])
    ]
    return order(candidates, scores, k), time.perf_counter() - t0
