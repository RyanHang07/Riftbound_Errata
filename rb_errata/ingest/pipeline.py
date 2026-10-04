"""`dates` and `ingest`: from fetched files to dated, embedded chunks.

Writes two committed files (brief section 7: everything about the corpus
except the corpus):
- data/effective_dates.json: every effective date, its source and candidates.
- data/corpus.json: every chunk's ref, dates, hash and token count. No text.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from rb_errata import db
from rb_errata.config import Settings
from rb_errata.ingest.chunk import Chunk, chunk_rules
from rb_errata.ingest.dates import Interval, find_effective_date, intervals
from rb_errata.ingest.fetch import FETCH_LOG, RAW, patch_notes_path, sha1_of
from rb_errata.ingest.pdf import extract_text, printed_date
from rb_errata.ingest.rules import parse_rules
from rb_errata.ingest.sources import CORE_RULES, RulesDoc
from rb_errata.ollama import Ollama, checked_digest

EFFECTIVE_DATES = Path("data/effective_dates.json")
CORPUS = Path("data/corpus.json")
EMBED_BATCH = 32
TOKENIZER = "cl100k_base"


def token_counter() -> Callable[[str], int]:
    import tiktoken  # imported here so contract tests never need its data file

    enc = tiktoken.get_encoding(TOKENIZER)
    return lambda s: len(enc.encode(s))


def run_dates(raw: Path = RAW) -> list[str]:
    results = []
    for doc in CORE_RULES:
        page = patch_notes_path(doc, raw)
        html = page.read_text() if doc.patch_notes and page.exists() else None
        r = find_effective_date(doc.version, doc.patch_notes, html)
        if html is not None:
            r.page_sha1 = hashlib.sha1(html.encode()).hexdigest()
        results.append(r)
    EFFECTIVE_DATES.write_text(json.dumps([r.as_dict() for r in results], indent=2) + "\n")
    return [
        f"{r.status:<8}{r.version:<6}{r.effective or '-':<12}{r.basis or '-':<18}{r.reason} "
        f"({len(r.candidates)} candidate phrases)"
        for r in results
    ]


def run_dates_debug(raw: Path = RAW) -> list[str]:
    from rb_errata.ingest.dates import debug_page

    lines = []
    for doc in CORE_RULES:
        page = patch_notes_path(doc, raw)
        if not doc.patch_notes or not page.exists():
            continue
        lines.append(f"\n=== {doc.version}  {doc.patch_notes}")
        lines += debug_page(page.read_text())
    return lines


def _load_effective() -> dict[str, date | None]:
    if not EFFECTIVE_DATES.exists():
        raise SystemExit("data/effective_dates.json missing: run `make dates` first")
    rows = json.loads(EFFECTIVE_DATES.read_text())
    return {
        r["version"]: date.fromisoformat(r["effective"]) if r["status"] == "known" else None
        for r in rows
    }


def _embed_all(
    conn: Any, client: Ollama, settings: Settings, digest: str, texts: list[str]
) -> list[str]:
    """Vector literals for `texts`, from the cache where possible."""
    prefix = settings.embed_doc_prefix
    hashes = [hashlib.sha256(t.encode()).hexdigest() for t in texts]
    cached = dict(
        conn.execute(
            "SELECT content_hash, embedding::text FROM embedding_cache "
            "WHERE model_digest = %s AND prefix = %s AND content_hash = ANY(%s)",
            (digest, prefix, hashes),
        ).fetchall()
    )
    todo = [i for i, h in enumerate(hashes) if h not in cached]
    for start in range(0, len(todo), EMBED_BATCH):
        batch = todo[start : start + EMBED_BATCH]
        vectors = client.embed([prefix + texts[i] for i in batch])
        for i, v in zip(batch, vectors, strict=True):
            if len(v) != settings.embed_dims:
                raise SystemExit(f"embedder returned {len(v)} dims, expected {settings.embed_dims}")
            lit = db.vector_literal(v)
            conn.execute(
                "INSERT INTO embedding_cache VALUES (%s, %s, %s, %s::vector) "
                "ON CONFLICT DO NOTHING",
                (hashes[i], digest, prefix, lit),
            )
            cached[hashes[i]] = lit
    return [cached[h] for h in hashes]


def doc_chunks(
    doc: RulesDoc, count: Callable[[str], int], raw: Path = RAW
) -> tuple[date, list[Chunk]]:
    path = raw / doc.filename
    if not path.exists() or sha1_of(path) != doc.sha1:
        raise SystemExit(f"{doc.id}: verified PDF missing, run `make fetch`")
    text = extract_text(path)
    return printed_date(text), chunk_rules(parse_rules(text), count)


def manifest_entry(
    doc: RulesDoc, c: Chunk, iv: Interval, printed: date, tokens: int
) -> dict[str, Any]:
    """One chunk's committed record: everything about it except its text."""
    return {
        "source_doc": doc.filename, "source_ref": f"{doc.id}:{c.source_ref}", "refs": list(c.refs),
        "kind": "rule", "published_at": printed.isoformat(),
        "valid_from": iv.valid_from.isoformat(),
        "valid_to": iv.valid_to.isoformat() if iv.valid_to else None,
        "content_hash": "sha256:" + hashlib.sha256(c.text.encode()).hexdigest(), "tokens": tokens,
    }  # fmt: skip


def chunks_sha256(entries: list[dict[str, Any]]) -> str:
    """One fingerprint for a whole manifest's chunk list, so two ingestions on
    different machines can be compared without exchanging the file."""
    return hashlib.sha256(json.dumps(entries, sort_keys=True).encode()).hexdigest()


def run_ingest(settings: Settings, raw: Path = RAW) -> list[str]:
    count = token_counter()
    effective = _load_effective()
    sources = json.loads(FETCH_LOG.read_text()) if FETCH_LOG.exists() else {}
    printed, chunked = {}, {}
    for doc in CORE_RULES:
        printed[doc.version], chunked[doc.version] = doc_chunks(doc, count, raw)
    ok, refused = intervals([d.version for d in CORE_RULES], effective, printed)

    lines = [f"refused  {v}: {why}" for v, why in refused.items()]
    manifest: list[dict[str, Any]] = []
    client = Ollama(settings)
    try:
        digest = checked_digest(client, settings.embed_model, settings.embed_digest)
        db.reset(settings)
        with db.connect(settings) as conn:
            for doc in CORE_RULES:
                if doc.version not in ok:
                    continue
                iv, chunks = ok[doc.version], chunked[doc.version]
                conn.execute(
                    "INSERT INTO documents VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                    (doc.id, doc.doc, doc.version, doc.sha1, sources.get(doc.id, doc.urls[0]),
                     doc.provenance, printed[doc.version], iv.valid_from, iv.valid_to),
                )  # fmt: skip
                vectors = _embed_all(conn, client, settings, digest, [c.text for c in chunks])
                for c, vec in zip(chunks, vectors, strict=True):
                    h = hashlib.sha256(c.text.encode()).hexdigest()
                    n = count(c.text)
                    ref = f"{doc.id}:{c.source_ref}"
                    conn.execute(
                        "INSERT INTO chunks (document_id, kind, source_ref, refs, text, tokens, "
                        "embedding, valid_from, valid_to, published_at, model_tag, model_digest, "
                        "content_hash) VALUES (%s,'rule',%s,%s,%s,%s,%s::vector,%s,%s,%s,%s,%s,%s)",
                        (doc.id, ref, list(c.refs), c.text, n, vec, iv.valid_from, iv.valid_to,
                         printed[doc.version], settings.embed_model, digest, f"sha256:{h}"),
                    )  # fmt: skip
                    manifest.append(manifest_entry(doc, c, iv, printed[doc.version], n))
                window = f"{iv.valid_from} to {iv.valid_to or 'now'}"
                lines.append(f"ingested {doc.id}: {len(chunks)} chunks, valid {window}")
    finally:
        client.close()

    from rb_errata.config import DEFAULT_EMBED_PROFILE

    if settings.embed_profile != DEFAULT_EMBED_PROFILE and CORPUS.exists():
        # Another embedder over the SAME chunks: data/corpus.json describes
        # them already and stays as it is. If the chunks differ, the two
        # embedders would be compared on different corpora, which is not a
        # comparison of embedders.
        committed = json.loads(CORPUS.read_text())["chunks_sha256"]
        if chunks_sha256(manifest) != committed:
            raise SystemExit("chunks differ from data/corpus.json; embedders must share a corpus")
        lines.append(f"chunks match data/corpus.json ({committed[:12]}); file left unchanged")
        return lines

    CORPUS.write_text(
        json.dumps(
            {
                "ingested_at": datetime.now(UTC).isoformat(timespec="seconds"),
                "embed_model": settings.embed_model,
                "embed_digest": digest,
                "tokenizer": TOKENIZER,
                "chunks_sha256": chunks_sha256(manifest),
                "chunks": manifest,
            },
            indent=1,
        )
        + "\n"
    )
    return lines
