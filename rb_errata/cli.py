"""Command line entry point: `python -m rb_errata.cli <command>`.

Commands are added as slices earn them. Slice 0 has `doctor` and `init-db`;
`ingest`, `eval` and `ablate` do not exist yet on purpose.
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
    print("pgvector extension ensured")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="rb_errata")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("doctor", help="can the pipeline run at all? no corpus needed").set_defaults(
        fn=_doctor
    )
    sub.add_parser("init-db", help="ensure the pgvector extension exists").set_defaults(fn=_init_db)
    args = parser.parse_args(argv)
    code: int = args.fn(args)
    return code


if __name__ == "__main__":
    sys.exit(main())
