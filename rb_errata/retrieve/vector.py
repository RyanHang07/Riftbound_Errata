"""Naive vector retrieval: nearest chunks by cosine distance, nothing else.

NO DATE FILTER, ON PURPOSE. This is the baseline slice 3 exists to break: asked
about July 2026, it will happily return a December 2025 rule if that text is
closer to the question. The eventual signature is search_rules(query, as_of);
slice 10 adds the as_of predicate, and this function stays as the baseline
the improvement is measured against.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from rb_errata import db
from rb_errata.config import Settings
from rb_errata.ollama import Ollama


@dataclass(frozen=True)
class Passage:
    source_ref: str
    refs: list[str]
    text: str
    distance: float
    valid_from: date
    valid_to: date | None


def search(settings: Settings, client: Ollama, query: str, k: int = 5) -> list[Passage]:
    vec = db.vector_literal(client.embed([settings.embed_query_prefix + query])[0])
    with db.connect(settings) as conn:
        rows = conn.execute(
            "SELECT source_ref, refs, text, embedding <=> %s::vector AS d, valid_from, valid_to "
            "FROM chunks ORDER BY d LIMIT %s",
            (vec, k),
        ).fetchall()
    return [Passage(str(r[0]), list(r[1]), str(r[2]), float(r[3]), r[4], r[5]) for r in rows]  # type: ignore[arg-type,call-overload]
