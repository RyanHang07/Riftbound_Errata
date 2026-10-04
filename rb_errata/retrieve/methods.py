"""Named retrieval configurations, the rows of the ablation table.

Every recall run records which one produced it, and `make recall-compare`
pairs two runs question by question. Adding a retrieval change means adding
a name here, so no configuration is ever measured without one.
"""

from __future__ import annotations

from datetime import date

from rb_errata.config import Settings
from rb_errata.ollama import Ollama
from rb_errata.retrieve import lexical, vector
from rb_errata.retrieve.vector import Passage

METHODS = {
    "naive": "naive-vector, no date filter",
    "as-of": "vector, as_of filter before ranking",
    "lexical": "postgres full-text (stemmed terms ORed), as_of filter",
    "hybrid": "RRF(vector, full-text) k=60 over top 50 each, as_of filter",
}

# Reciprocal rank fusion (Cormack, Clarke and Buettcher, SIGIR 2009):
# score = sum over lists of 1 / (RRF_K + rank). It uses ranks only, so it
# needs no calibration between a cosine distance and a ts_rank score, which
# live on unrelated scales. 60 is the paper's constant; it is not tuned here,
# because tuning it on the evaluation questions would overfit them.
RRF_K = 60
FUSE_DEPTH = 50


def rrf(lists: list[list[Passage]], k: int) -> list[Passage]:
    """Fuse ranked lists. Pure; unit-tested. Ties keep the first list's order."""
    score: dict[str, float] = {}
    first: dict[str, tuple[int, int, Passage]] = {}
    for li, ranked in enumerate(lists):
        for rank, p in enumerate(ranked, 1):
            key = p.source_ref + "|" + p.content_hash
            score[key] = score.get(key, 0.0) + 1.0 / (RRF_K + rank)
            first.setdefault(key, (li, rank, p))
    order = sorted(score, key=lambda key: (-score[key], first[key][0], first[key][1]))
    out = []
    for key in order[:k]:
        p = first[key][2]
        out.append(
            Passage(
                p.source_ref, p.refs, p.text, -score[key], p.valid_from, p.valid_to, p.content_hash
            )
        )
    return out


def retrieve(
    method: str, settings: Settings, client: Ollama, query: str, k: int, as_of: date
) -> list[Passage]:
    if method == "naive":
        return vector.search(settings, client, query, k)
    if method == "as-of":
        return vector.search(settings, client, query, k, as_of=as_of)
    if method == "lexical":
        return lexical.search(settings, query, k, as_of=as_of)
    if method == "hybrid":
        depth = max(k, FUSE_DEPTH)
        return rrf(
            [
                vector.search(settings, client, query, depth, as_of=as_of),
                lexical.search(settings, query, depth, as_of=as_of),
            ],
            k,
        )
    raise ValueError(f"unknown method {method!r}; one of {sorted(METHODS)}")
