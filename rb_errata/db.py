"""Database connection and schema.

The database is derived data: everything in it can be rebuilt from the fetched
documents plus `make ingest`. That is why the schema is created with plain
CREATE IF NOT EXISTS and changed by `make db-reset` rather than migrations, for
now. When the database holds something that cannot be rebuilt (eval runs are
committed as JSON instead), this stops being true and migrations arrive.
"""

from __future__ import annotations

import psycopg

from rb_errata.config import Settings


def connect(settings: Settings, *, timeout_s: int = 5) -> psycopg.Connection[tuple[object, ...]]:
    # A short connect timeout: doctor must report "unreachable" in seconds,
    # not hang for the OS default of minutes when the container is down.
    # search_path picks the embedder profile's schema (Settings.db_schema), so
    # every query below runs unchanged against whichever corpus is selected.
    # `public` stays on the path for the vector type itself.
    return psycopg.connect(
        settings.database_url,
        connect_timeout=timeout_s,
        autocommit=True,
        options=f"-c search_path={settings.db_schema},public",
    )


def schema(dims: int, name: str = "public") -> str:
    return f"""
CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA public;
CREATE SCHEMA IF NOT EXISTS {name};
SET search_path TO {name}, public;

-- One row per document version: where it came from and when it was the rule.
CREATE TABLE IF NOT EXISTS documents (
  id            text PRIMARY KEY,        -- 'core@1.4'
  doc           text NOT NULL,
  version       text NOT NULL,
  sha1          text NOT NULL,           -- the exact bytes ingested
  source_url    text NOT NULL,
  provenance    text NOT NULL,           -- 'cdn-verified' | 'mirror-only-unverified'
  published_at  date NOT NULL,           -- printed "Last Updated"
  valid_from    date NOT NULL,           -- effective date, from patch notes (A16)
  valid_to      date                     -- NULL means "still current", never a sentinel
);

CREATE TABLE IF NOT EXISTS chunks (
  id            bigserial PRIMARY KEY,
  document_id   text NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
  kind          text NOT NULL,           -- 'rule' for now; 'card' | 'faq' | 'errata' later
  source_ref    text NOT NULL,           -- 'core@1.4:315.2'
  refs          text[] NOT NULL,         -- every rule number inside: recall hits match on these
  text          text NOT NULL,
  tokens        integer NOT NULL,        -- cl100k, counted
  embedding     vector({dims}) NOT NULL,
  -- Copied from the document so the as_of predicate (slice 10) is one table.
  valid_from    date NOT NULL,
  valid_to      date,
  published_at  date NOT NULL,
  model_tag     text NOT NULL,           -- which embedder produced `embedding`
  model_digest  text NOT NULL,           -- ...and exactly which weights (A3)
  content_hash  text NOT NULL
);
-- No vector index, on purpose (A2): an exact scan over a few thousand rows
-- takes milliseconds and never drops rows that a date filter would keep.
CREATE INDEX IF NOT EXISTS chunks_validity ON chunks (valid_from, valid_to);

-- Embed an unchanged text once, ever, per model and prefix (brief section 7).
-- Keyed by digest, not tag: a re-pushed tag must not reuse old vectors.
CREATE TABLE IF NOT EXISTS embedding_cache (
  content_hash  text NOT NULL,
  model_digest  text NOT NULL,
  prefix        text NOT NULL,
  embedding     vector({dims}) NOT NULL,
  PRIMARY KEY (content_hash, model_digest, prefix)
);
"""


def init(settings: Settings) -> None:
    """Idempotent: creates whatever is missing."""
    with connect(settings) as conn:
        conn.execute(schema(settings.embed_dims, settings.db_schema))


def reset(settings: Settings) -> None:
    """Drop the derived tables and recreate them. The cache survives on purpose:
    it is keyed by content and model, so it stays valid across re-chunking."""
    with connect(settings) as conn:
        # Schema-qualified on purpose. Unqualified, a profile whose tables do
        # not exist yet would resolve `chunks` through search_path to
        # public.chunks and drop the nomic corpus.
        s = settings.db_schema
        conn.execute(f"CREATE SCHEMA IF NOT EXISTS {s}")
        conn.execute(f"DROP TABLE IF EXISTS {s}.chunks, {s}.documents")
        conn.execute(schema(settings.embed_dims, s))


def vector_literal(v: list[float]) -> str:
    return "[" + ",".join(f"{x:.8g}" for x in v) + "]"
