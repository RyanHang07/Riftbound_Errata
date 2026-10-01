"""Command line entry point: `python -m rb_errata.cli <command>`.

Commands are added as slices earn them. `eval` and `ablate` do not exist yet
on purpose.
"""

from __future__ import annotations

import argparse
import sys

from rb_errata import config, db, doctor


def _doctor(_: argparse.Namespace) -> int:
    settings = config.load()
    checks = doctor.run(settings)
    print(doctor.render(checks, doctor.host_fingerprint()))
    return doctor.exit_code(checks)


def _init_db(_: argparse.Namespace) -> int:
    db.init(config.load())
    print("schema ensured")
    return 0


def _fetch(_: argparse.Namespace) -> int:
    from rb_errata.ingest.fetch import fetch_all

    lines, ok = fetch_all()
    print("\n".join(lines))
    return 0 if ok else 1


def _dates(args: argparse.Namespace) -> int:
    from rb_errata.ingest.pipeline import run_dates, run_dates_debug

    if args.debug:
        print("\n".join(run_dates_debug()))
        return 0

    print("status  ver   effective   reason")
    print("\n".join(run_dates()))
    return 0


def _inspect(_: argparse.Namespace) -> int:
    """Parse and chunk every fetched PDF; no database, no model. Free."""
    from rb_errata.ingest.pipeline import doc_chunks, token_counter
    from rb_errata.ingest.sources import CORE_RULES

    count = token_counter()
    for doc in CORE_RULES:
        printed, chunks = doc_chunks(doc, count)
        sizes = sorted(count(c.text) for c in chunks)
        refs = {r for c in chunks for r in c.refs}
        print(
            f"{doc.id:<9} printed {printed}  rules {len(refs):>5}  chunks {len(chunks):>5}  "
            f"tokens median {sizes[len(sizes) // 2]:>3} max {sizes[-1]:>4} total {sum(sizes):>7,}"
        )
    return 0


def _ingest(_: argparse.Namespace) -> int:
    from rb_errata.ingest.pipeline import run_ingest

    print("\n".join(run_ingest(config.load())))
    return 0


def _search(args: argparse.Namespace) -> int:
    from rb_errata.ollama import Ollama
    from rb_errata.retrieve.vector import search

    settings = config.load()
    client = Ollama(settings)
    try:
        passages = search(settings, client, args.query, args.k)
    finally:
        client.close()
    print("NAIVE SEARCH: no date filter. Results may come from any rules version.\n")
    for i, p in enumerate(passages, 1):
        window = f"{p.valid_from} to {p.valid_to or 'now'}"
        print(f"{i}. {p.source_ref}  (valid {window})  distance {p.distance:.3f}")
        print("   " + p.text[:300].replace("\n", "\n   ") + ("..." if len(p.text) > 300 else ""))
        print()
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="rb_errata")
    sub = parser.add_subparsers(dest="command", required=True)
    commands = {
        "doctor": (_doctor, "can the pipeline run at all? no corpus needed"),
        "init-db": (_init_db, "create the schema if missing"),
        "fetch": (_fetch, "download sources into data/raw (SHA-1 verified)"),
        "dates": (_dates, "parse effective dates from patch notes"),
        "inspect": (_inspect, "parse and chunk fetched PDFs; no database, no model"),
        "ingest": (_ingest, "chunk, embed and store every datable version"),
        "search": (_search, "naive vector search, no date filter"),
    }
    for name, (fn, help_text) in commands.items():
        p = sub.add_parser(name, help=help_text)
        p.set_defaults(fn=fn)
        if name == "dates":
            p.add_argument("--debug", action="store_true", help="show date mentions in context")
        if name == "search":
            p.add_argument("query")
            p.add_argument("-k", type=int, default=5)
    args = parser.parse_args(argv)
    code: int = args.fn(args)
    return code


if __name__ == "__main__":
    sys.exit(main())
