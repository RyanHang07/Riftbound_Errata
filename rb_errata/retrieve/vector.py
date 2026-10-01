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
    source_ref: str  # "core@1.3:419.4"
    refs: list[str]  # bare rule numbers inside the chunk
    text: str
    distance: float
    valid_from: date
    valid_to: date | None
    content_hash: str

    @property
    def document(self) -> str:
        return self.source_ref.split(":", 1)[0]  # "core@1.3"

    @property
    def qualified_refs(self) -> set[str]:
        """Rule numbers qualified by version, the form labels use (A16)."""
        return {f"{self.document}:{r}" for r in self.refs}

    def in_effect_on(self, day: date) -> bool:
        return self.valid_from <= day and (self.valid_to is None or day < self.valid_to)


def search(settings: Settings, client: Ollama, query: str, k: int = 5) -> list[Passage]:
    vec = db.vector_literal(client.embed([settings.embed_query_prefix + query])[0])
    with db.connect(settings) as conn:
        rows = conn.execute(
            "SELECT source_ref, refs, text, embedding <=> %s::vector AS d, valid_from, valid_to, "
            "content_hash FROM chunks ORDER BY d LIMIT %s",
            (vec, k),
        ).fetchall()
    return [
        Passage(str(r[0]), list(r[1]), str(r[2]), float(r[3]), r[4], r[5], str(r[6]))  # type: ignore[arg-type,call-overload]
        for r in rows
    ]
