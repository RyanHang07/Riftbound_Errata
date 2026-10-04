"""Keyword retrieval with Postgres full-text search (slice 8).

Vectors match meaning and blur exact words; rules questions often turn on one
exact word ("countered", "Deflect", "Finalized"). Full-text search matches
those words after stemming ("countered" and "counter" meet).

OR, not AND. `plainto_tsquery` joins every question word with AND, and a
chunk containing all of "does abandoned hall trigger if the spell is
countered" does not exist (card names are not in the corpus). The query is
rewritten to OR the same stemmed terms, and ranking decides.

ts_rank_cd normalisation 1 (divide by 1 + log(length)): without it a long
chunk wins by containing more of the words, not by being about them.
"""

from __future__ import annotations

from datetime import date

from rb_errata import db
from rb_errata.config import Settings
from rb_errata.retrieve.vector import IN_EFFECT, Passage

# The question's stemmed terms, ORed. Empty when every word is a stopword,
# which matches nothing; the hybrid then falls back to the vector list.
OR_QUERY = "replace(plainto_tsquery('english', %(q)s)::text, ' & ', ' | ')::tsquery"


def search(settings: Settings, query: str, k: int = 5, as_of: date | None = None) -> list[Passage]:
    where = f"AND {IN_EFFECT} " if as_of else ""
    with db.connect(settings) as conn:
        rows = conn.execute(
            f"SELECT source_ref, refs, text, ts_rank_cd(tsv, {OR_QUERY}, 1) AS r, valid_from, "
            f"valid_to, content_hash FROM {settings.db_schema}.chunks "
            f"WHERE tsv @@ {OR_QUERY} {where}ORDER BY r DESC, id LIMIT %(k)s",
            {"q": query, "k": k, "as_of": as_of},
        ).fetchall()
    # distance = -rank so that, as for vectors, lower is better.
    return [
        Passage(str(r[0]), list(r[1]), str(r[2]), -float(r[3]), r[4], r[5], str(r[6]))  # type: ignore[arg-type,call-overload]
        for r in rows
    ]
