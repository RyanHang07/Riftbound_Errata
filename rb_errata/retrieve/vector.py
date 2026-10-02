"""Vector retrieval: nearest chunks by cosine distance, with or without dates.

Two modes, one function, so the comparison is exactly one predicate:
- as_of None, the naive baseline. Asked about July 2026, it will happily
  return a December 2025 rule if that text is closer to the question. Slice 3
  captured this; slice 5 measured it (A24).
- as_of a date, version-aware (slice 6, brief section 5 "Filter by as_of
  before ranking"). Chunks not in effect on that date are removed in SQL
  BEFORE similarity ranks anything, so an outdated rule never enters the
  candidate set and the generator is never asked to resolve two versions.
  With an exact scan (A2) the filter cannot cost recall: in-effect chunks
  keep their order and only lose competitors, so a hit can only move up.
  (An approximate index filtered after the scan could lose hits; A2 is why
  this guarantee holds.)
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


# Half-open [valid_from, valid_to): on the day a new version takes effect the
# old one is already out. Same rule as Passage.in_effect_on; a test holds them
# together, because two definitions of "in effect" would disagree on exactly
# the boundary days the project is about.
IN_EFFECT = "valid_from <= %(as_of)s AND (valid_to IS NULL OR %(as_of)s < valid_to)"


def search(
    settings: Settings, client: Ollama, query: str, k: int = 5, as_of: date | None = None
) -> list[Passage]:
    vec = db.vector_literal(client.embed([settings.embed_query_prefix + query])[0])
    # Schema-qualified: unqualified, a profile not yet ingested would fall
    # through search_path to another embedder's table.
    where = f"WHERE {IN_EFFECT} " if as_of else ""
    with db.connect(settings) as conn:
        rows = conn.execute(
            "SELECT source_ref, refs, text, embedding <=> %(vec)s::vector AS d, valid_from, "
            f"valid_to, content_hash FROM {settings.db_schema}.chunks {where}"
            "ORDER BY d LIMIT %(k)s",
            {"vec": vec, "k": k, "as_of": as_of},
        ).fetchall()
    return [
        Passage(str(r[0]), list(r[1]), str(r[2]), float(r[3]), r[4], r[5], str(r[6]))  # type: ignore[arg-type,call-overload]
        for r in rows
    ]
