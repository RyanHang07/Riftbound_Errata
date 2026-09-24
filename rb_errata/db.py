"""Database connection and schema.

Slice 0 owns only the pgvector extension. The chunks table arrives in slice 2,
once slice 1 has shown what the corpus actually needs.
"""

from __future__ import annotations

import psycopg

from rb_errata.config import Settings


def connect(settings: Settings, *, timeout_s: int = 5) -> psycopg.Connection[tuple[object, ...]]:
    # A short connect timeout: doctor must report "unreachable" in seconds,
    # not hang for the OS default of minutes when the container is down.
    return psycopg.connect(settings.database_url, connect_timeout=timeout_s, autocommit=True)


def init(settings: Settings) -> None:
    """Idempotent. Covers volumes created before db/init/ existed."""
    with connect(settings) as conn:
        conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
