"""Command line entry point: `python -m rb_errata.cli <command>`.

Commands are added as slices earn them. `eval` and `ablate` do not exist yet
on purpose.
"""

from __future__ import annotations

import argparse
import sys
from typing import TYPE_CHECKING

from rb_errata import config, db, doctor

if TYPE_CHECKING:
    from rb_errata.ingest.rules import Rule


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
    from datetime import date

    from rb_errata.ollama import Ollama
    from rb_errata.retrieve.methods import METHODS, retrieve

    settings = config.load()
    as_of = date.fromisoformat(args.as_of) if args.as_of else None
    method = args.method or ("as-of" if as_of else "naive")
    if method != "naive" and as_of is None:
        print(f"error: method {method} needs --as-of YYYY-MM-DD", file=sys.stderr)
        return 1
    db.init(settings)
    client = Ollama(settings)
    try:
        passages = retrieve(method, settings, client, args.query, args.k, as_of or date.today())
    finally:
        client.close()
    if as_of:
        print(f"{METHODS[method].upper()}: only rules in effect on {as_of}.\n")
    else:
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


def _recall(args: argparse.Namespace) -> int:
    from rb_errata.recall import run

    out = run(config.load(), args.method)
    print((out / "report.md").read_text())
    print(f"snapshot and report written to {out}/")
    return 0


def _recall_report(args: argparse.Namespace) -> int:
    from pathlib import Path

    from rb_errata.recall import report

    print("\n".join(report(Path(args.dir))))
    return 0


def _recall_compare(args: argparse.Namespace) -> int:
    from pathlib import Path

    from rb_errata.recall import compare

    print("\n".join(compare(Path(args.a), Path(args.b))))
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


def _questions(args: argparse.Namespace) -> int:
    """Build evals/questions.yaml from the pinned rulings clone + the diff questions."""
    import collections
    from pathlib import Path

    from rb_errata.ingest.fetch import RAW
    from rb_errata.ingest.pdf import extract_text
    from rb_errata.ingest.rules import parse_rules
    from rb_errata.ingest.sources import CORE_RULES
    from rb_errata.labels.build import build

    versions = {
        d.version: parse_rules(extract_text(Path(RAW) / d.filename))
        for d in CORE_RULES
        if d.version != "1.0"  # refused at ingestion (A16): not in the corpus
    }
    entries, problems = build(Path(args.rulings), versions, CORE_RULES[-1].version)
    strata = collections.Counter(e["stratum"] for e in entries)
    print(f"{len(entries)} questions -> evals/questions.yaml: {dict(strata)}")
    for p in problems:
        print(f"PROBLEM {p}")
    return 1 if problems else 0


def _versions() -> dict[str, list[Rule]]:
    from pathlib import Path

    from rb_errata.ingest.fetch import RAW
    from rb_errata.ingest.pdf import extract_text
    from rb_errata.ingest.rules import parse_rules
    from rb_errata.ingest.sources import CORE_RULES

    return {
        d.version: parse_rules(extract_text(Path(RAW) / d.filename))
        for d in CORE_RULES
        if d.version != "1.0"  # refused at ingestion (A16): not in the corpus
    }


def _counterparts(_: argparse.Namespace) -> int:
    """Align every expected rule to its copies in other versions (needs data/raw)."""
    from rb_errata.labels import counterparts
    from rb_errata.labels.review import load_questions

    n = counterparts.write(_versions(), load_questions())
    print(f"{n} expected refs aligned -> {counterparts.COUNTERPARTS}")
    return 0


def _site_data(_: argparse.Namespace) -> int:
    from rb_errata.site_data import write

    print(f"wrote {write()}")
    return 0


def _power(_: argparse.Namespace) -> int:
    from rb_errata.labels.power import report

    print("\n".join(report()))
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
        "search": (_search, "vector search; --as-of YYYY-MM-DD filters to rules then in effect"),
        "diff": (_diff, "rules whose text changed between two versions"),
        "drift": (_drift, "run the slice 3 drift candidates and write fixtures"),
        "show": (_show, "re-display a fixture with rule text from the local database"),
        "regrade": (_regrade, "re-grade stored fixtures against the current labels"),
        "check-candidates": (_check_candidates, "full text of every candidate rule, per version"),
        "questions": (_questions, "build evals/questions.yaml (needs the rulings clone)"),
        "counterparts": (_counterparts, "align expected rules to other versions (needs data/raw)"),
        "recall": (_recall, "slice 5: retrieve top 20 for every question, snapshot, report"),
        "recall-report": (_recall_report, "recompute a recall report from a committed snapshot"),
        "recall-compare": (_recall_compare, "pair two recall runs: discordant counts, McNemar"),
        "site-data": (_site_data, "export numbers-only site/data/results.json from committed runs"),
        "power": (_power, "how many questions are needed (exact, no model)"),
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
        if name == "questions":
            p.add_argument("rulings", help="path to a clone of ChristianIvicevic/riftboundfaq")
        if name in ("regrade", "recall-report"):
            p.add_argument("dir")
        if name == "recall":
            p.add_argument("--method", default="naive", help="naive | as-of | lexical | hybrid")
        if name == "recall-compare":
            p.add_argument("a")
            p.add_argument("b")
        if name == "search":
            p.add_argument("query")
            p.add_argument("-k", type=int, default=5)
            p.add_argument("--as-of", help="YYYY-MM-DD; omit for the naive baseline")
            p.add_argument("--method", help="as-of | lexical | hybrid (default: as-of with a date)")
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
