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

    print("status  ver   effective   basis             reason")
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


def _diff(args: argparse.Namespace) -> int:
    """Rules whose text changed between two versions, most meaning-flipping first.
    Prints excerpts of Riot's text to the terminal only."""
    from pathlib import Path

    from rb_errata.ingest.align import align, flip_score, normalise, word_diff
    from rb_errata.ingest.fetch import RAW
    from rb_errata.ingest.pdf import extract_text
    from rb_errata.ingest.rules import parse_rules

    def rules(v: str) -> list:  # type: ignore[type-arg]
        return parse_rules(extract_text(Path(RAW) / f"core-rules-v{v}.pdf"))

    matches, added = align(rules(args.old), rules(args.new))
    kinds: dict[str, int] = {}
    for m in matches:
        kinds[m.kind] = kinds.get(m.kind, 0) + 1
    print(f"v{args.old} -> v{args.new}: {kinds}, added {len(added)}")
    # (old, new) pairs whose text differs beyond cross-reference renumbering.
    changed = [
        (m.old, m.new, m.similarity) for m in matches
        if m.new is not None and m.kind == "changed"
        and normalise(m.old.text) != normalise(m.new.text)
    ]  # fmt: skip
    changed.sort(key=lambda x: (-flip_score(x[0].text, x[1].text), x[2]))
    for old, new, sim in changed[: args.n]:
        print(f"\n[{args.old}:{old.number} -> {args.new}:{new.number}] sim {sim:.2f}")
        print("   " + word_diff(old.text, new.text)[:500])
    return 0


def _drift(_: argparse.Namespace) -> int:
    from rb_errata.drift import run

    print("\n".join(run(config.load())))
    return 0


def _regrade(args: argparse.Namespace) -> int:
    from pathlib import Path

    from rb_errata.drift import regrade_dir

    print("\n".join(regrade_dir(Path(args.dir))))
    return 0


def _check_candidates(_: argparse.Namespace) -> int:
    from rb_errata.drift import check_candidates

    print("\n".join(check_candidates()))
    return 0


def _show(args: argparse.Namespace) -> int:
    from pathlib import Path

    from rb_errata.drift import show

    print("\n".join(show(config.load(), Path(args.fixture))))
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
        "diff": (_diff, "rules whose text changed between two versions"),
        "drift": (_drift, "run the slice 3 drift candidates and write fixtures"),
        "show": (_show, "re-display a fixture with rule text from the local database"),
        "regrade": (_regrade, "re-grade stored fixtures against the current labels"),
        "check-candidates": (_check_candidates, "full text of every candidate rule, per version"),
    }
    for name, (fn, help_text) in commands.items():
        p = sub.add_parser(name, help=help_text)
        p.set_defaults(fn=fn)
        if name == "dates":
            p.add_argument("--debug", action="store_true", help="show date mentions in context")
        if name == "diff":
            p.add_argument("old")
            p.add_argument("new")
            p.add_argument("-n", type=int, default=15)
        if name == "show":
            p.add_argument("fixture")
        if name == "regrade":
            p.add_argument("dir")
        if name == "search":
            p.add_argument("query")
            p.add_argument("-k", type=int, default=5)
    args = parser.parse_args(argv)
    from rb_errata.ollama import PinError

    try:
        code: int = args.fn(args)
    except PinError as exc:
        # An unpinned model is a setup step, not a crash: say what to do.
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return code


if __name__ == "__main__":
    sys.exit(main())
