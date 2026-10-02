"""Where each expected rule lives in the other versions, by text alignment.

Slice 5 needs this for one secondary metric: how often an outdated copy of an
expected rule is retrieved next to (or instead of) the right one (A20). A15
forbids finding that copy by rule number, because hundreds of rules keep their
text under a new number at every update; `core@1.3:419.4.a` and
`core@1.4:419.4.a` can be different rules. So the copy is found the way
`make diff` finds it: word 3-gram alignment of the two versions' texts.

The headline metric never reads this file. A16 rejected a cross-version map
for labels because an alignment mistake would silently corrupt them; here a
mistake can only miscount contamination, and every pair is committed in
evals/counterparts.json (refs and a same-text flag, no rule text) so it can
be audited.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from rb_errata.ingest.align import align, normalise
from rb_errata.ingest.rules import Rule

COUNTERPARTS = Path("evals/counterparts.json")


def _vkey(v: str) -> tuple[int, ...]:
    return tuple(int(x) for x in v.split("."))


def counterparts(
    versions: dict[str, list[Rule]], wanted: set[str], doc: str = "core"
) -> dict[str, list[dict[str, Any]]]:
    """For each `core@V:R` in `wanted`: its aligned rule in every other version.

    Each entry is {"ref": "core@W:R2", "same_text": bool}. A version where the
    rule has no match (added later, or removed) is simply absent.
    """
    by_version: dict[str, set[str]] = {}
    for q in wanted:
        d, num = q.split(":", 1)
        by_version.setdefault(d.split("@", 1)[1], set()).add(num)

    out: dict[str, list[dict[str, Any]]] = {q: [] for q in sorted(wanted)}
    for v, nums in by_version.items():
        for w in sorted(versions, key=_vkey):
            if w == v:
                continue
            older = _vkey(w) < _vkey(v)
            # align() reports every rule of its first argument, so the version
            # being searched for goes second when it is the newer one.
            matches, _ = (
                align(versions[w], versions[v]) if older else align(versions[v], versions[w])
            )
            for m in matches:
                if m.new is None:
                    continue
                mine, theirs = (m.new, m.old) if older else (m.old, m.new)
                if mine.number in nums:
                    out[f"{doc}@{v}:{mine.number}"].append({
                        "ref": f"{doc}@{w}:{theirs.number}",
                        "same_text": normalise(mine.text) == normalise(theirs.text),
                    })  # fmt: skip
    return out


def write(versions: dict[str, list[Rule]], entries: list[dict[str, Any]]) -> int:
    wanted = {s for e in entries for s in e["expect_sources"]}
    data = counterparts(versions, wanted)
    COUNTERPARTS.write_text(json.dumps(data, indent=1, sort_keys=True) + "\n")
    return len(data)


def load(path: Path = COUNTERPARTS) -> dict[str, list[dict[str, Any]]]:
    data: dict[str, list[dict[str, Any]]] = json.loads(path.read_text())
    return data
