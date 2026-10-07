"""Slice 15: what the four MCP tools do, without the protocol (A41).

The server (rb_errata/server.py) is a thin wrapper, so every rule here is
tested without spawning anything. Each tool refuses bad input with a
`ToolError`: the SDK returns it to the model as an error result carrying the
message, where any other exception reaches the model only as "Error executing
tool". So every failure a user can cause, or fix, is a ToolError that says how.

Where the text comes from:
- `search_rules` runs the measured best configuration (A29: as-of, qwen3) and
  nothing else, so what Claude Desktop sees is what the Results page measured.
  It refuses a database whose chunks differ from data/corpus.json, the same
  guard `make recall` uses.
- `get_rule` and `what_changed` read the PDFs in data/raw/, parsed by the code
  that built the corpus, after checking each file's SHA-1 against the pin. Rule
  text is returned to the local client only; none enters the repository.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date
from functools import cache
from pathlib import Path
from typing import Any

from mcp.server.mcpserver.exceptions import ToolError

from rb_errata.ingest.align import align, flip_score, normalise
from rb_errata.ingest.rules import Rule
from rb_errata.ingest.sources import CORE_RULES
from rb_errata.retrieve.vector import Passage

CORPUS = Path("data/corpus.json")
EFFECTIVE = Path("data/effective_dates.json")
RAW = Path("data/raw")
DOC = "core"
SEARCH_METHOD = "as-of"  # A29's best; the server never offers a dropped method
K_MAX = 20
_REF = re.compile(r"^(?P<doc>[a-z]+)@v?(?P<version>\d+\.\d+):(?P<number>\d{3}(?:\.\w+)*)$")


def _vkey(v: str) -> tuple[int, ...]:
    return tuple(int(x) for x in v.split("."))


@dataclass(frozen=True)
class Window:
    version: str
    valid_from: date
    valid_to: date | None  # None: still current


@cache
def windows(corpus: Path = CORPUS) -> dict[str, Window]:
    """Each searchable version's validity window, read from the committed corpus."""
    seen: dict[str, Window] = {}
    for c in json.loads(corpus.read_text())["chunks"]:
        v = c["source_ref"].split(":", 1)[0].split("@", 1)[1]
        end = date.fromisoformat(c["valid_to"]) if c["valid_to"] else None
        seen.setdefault(v, Window(v, date.fromisoformat(c["valid_from"]), end))
    return dict(sorted(seen.items(), key=lambda x: _vkey(x[0])))


def _version(raw: str, field_name: str) -> str:
    v = raw.strip().removeprefix("v")
    known = windows()
    if v in known:
        return v
    refused = {d.version for d in CORE_RULES} - set(known)
    if v in refused:
        raise ToolError(
            f"{field_name}: version {v} has no known effective date, so it is not searchable "
            f"(see list_versions). Searchable: {', '.join(known)}."
        )
    raise ToolError(f"{field_name}: unknown version {raw!r}. Searchable: {', '.join(known)}.")


def _date(raw: str | None) -> date:
    if raw is None or raw == "":
        return date.today()
    try:
        day = date.fromisoformat(raw)
    except ValueError:
        raise ToolError(f"as_of: {raw!r} is not a date; use YYYY-MM-DD") from None
    first = next(iter(windows().values()))
    if day < first.valid_from:
        raise ToolError(
            f"as_of: {day} is before {first.valid_from}, when the first datable version "
            f"(v{first.version}) took effect. Earlier rules have no known dates."
        )
    return day


def parse_ref(ref: str) -> tuple[str, str]:
    """`core@1.4:419.4.a` -> ("1.4", "419.4.a"), or a ToolError saying the form."""
    m = _REF.match(ref.strip())
    if m is None:
        raise ToolError(f"ref: {ref!r} is not a rule reference; use the form core@1.4:419.4.a")
    if m["doc"] != DOC:
        raise ToolError(f"ref: only the Core Rules ({DOC}@...) are in the corpus, not {m['doc']}")
    return _version(m["version"], "ref"), m["number"]


# --- rule text from the local PDFs -------------------------------------------


@cache
def rules(version: str, raw: Path = RAW) -> dict[str, Rule]:
    """One version's rules by number. Parsed once per process (about 9 s a PDF)."""
    from rb_errata.ingest.fetch import sha1_of
    from rb_errata.ingest.pdf import extract_text
    from rb_errata.ingest.rules import parse_rules

    doc = next(d for d in CORE_RULES if d.version == version)
    path = raw / doc.filename
    if not path.exists():
        raise ToolError(f"{path} is missing; run `make fetch` in the project folder")
    if sha1_of(path) != doc.sha1:
        # Text from other bytes would be a different document under a pinned name.
        raise ToolError(f"{path} does not match its pinned SHA-1; run `make fetch` again")
    return {r.number: r for r in parse_rules(extract_text(path))}


def _window_fields(version: str) -> dict[str, Any]:
    w = windows()[version]
    return {
        "version": version,
        "valid_from": w.valid_from.isoformat(),
        "valid_to": w.valid_to.isoformat() if w.valid_to else None,
        "newer_version_exists": w.valid_to is not None,
    }


def get_rule(ref: str, load: Callable[[str], dict[str, Rule]] = rules) -> dict[str, Any]:
    version, number = parse_ref(ref)
    found = load(version).get(number)
    if found is None:
        raise ToolError(
            f"ref: core@{version} has no rule {number}. Rule numbers change between "
            "versions; search_rules finds a rule by meaning."
        )
    return {"ref": f"{DOC}@{version}:{number}", **_window_fields(version), "text": found.text}


# --- list_versions -------------------------------------------------------------


def list_versions(effective: Path = EFFECTIVE) -> dict[str, Any]:
    basis = {r["version"]: r for r in json.loads(effective.read_text())}
    known = windows()
    out = []
    for d in CORE_RULES:
        row = basis.get(d.version, {})
        if d.version in known:
            out.append({
                **_window_fields(d.version),
                "searchable": True,
                # Patch notes with no stated date fall back to the announcement
                # date; the tool says so instead of presenting it as exact.
                "date_basis": row.get("basis"),
            })  # fmt: skip
        else:
            out.append({
                "version": d.version,
                "searchable": False,
                "reason": row.get("reason") or "no known effective date",
            })  # fmt: skip
    return {"document": "Riftbound Core Rules", "versions": out}


# --- what_changed --------------------------------------------------------------


def _status(a: Rule, b: Rule) -> str:
    if normalise(a.text) != normalise(b.text):
        return "changed"
    return "unchanged" if a.number == b.number else "renumbered"


def what_changed(
    from_version: str,
    to_version: str,
    ref: str | None = None,
    limit: int = 20,
    load: Callable[[str], dict[str, Rule]] = rules,
) -> dict[str, Any]:
    old_v, new_v = _version(from_version, "from_version"), _version(to_version, "to_version")
    if _vkey(old_v) >= _vkey(new_v):
        raise ToolError(f"from_version {old_v} must be older than to_version {new_v}")
    if not 1 <= limit <= 100:
        raise ToolError("limit: between 1 and 100")
    target = None
    if ref is not None:
        target = parse_ref(ref)
        if target[0] not in (old_v, new_v):
            raise ToolError(f"ref: {ref} is from v{target[0]}, not v{old_v} or v{new_v}")
    old, new = load(old_v), load(new_v)
    # A15: matched by wording, never by number; numbers shift at every update.
    matches, added = align(list(old.values()), list(new.values()))

    def side(r: Rule | None, v: str) -> dict[str, Any] | None:
        return None if r is None else {"ref": f"{DOC}@{v}:{r.number}", "text": r.text}

    if target is not None:
        tv, num = target
        if num not in (old if tv == old_v else new):
            raise ToolError(f"ref: core@{tv} has no rule {num}")
        if tv == old_v:
            m = next(m for m in matches if m.old.number == num)
            status = "removed" if m.new is None else _status(m.old, m.new)
            return {"status": status, "old": side(m.old, old_v), "new": side(m.new, new_v)}
        hit = next((m for m in matches if m.new is not None and m.new.number == num), None)
        if hit is None:
            return {"status": "added", "old": None, "new": side(new[num], new_v)}
        assert hit.new is not None
        return {"status": _status(hit.old, hit.new), "old": side(hit.old, old_v),
                "new": side(hit.new, new_v)}  # fmt: skip

    changed = [m for m in matches if m.new is not None and _status(m.old, m.new) == "changed"]
    # Same order as `make diff`: wording that flips meaning (may/must, not) first.
    changed.sort(key=lambda m: (-flip_score(m.old.text, m.new.text), m.similarity))  # type: ignore[union-attr]
    removed = [m.old for m in matches if m.new is None]
    return {
        "from_version": old_v,
        "to_version": new_v,
        "counts": {"changed": len(changed), "added": len(added), "removed": len(removed)},
        "changed": [
            {"old": side(m.old, old_v), "new": side(m.new, new_v)} for m in changed[:limit]
        ],
        "added": [f"{DOC}@{new_v}:{r.number}" for r in added],
        "removed": [f"{DOC}@{old_v}:{r.number}" for r in removed],
    }


# --- search_rules --------------------------------------------------------------

Search = Callable[[str, int, date], list[Passage]]


@dataclass
class Backend:
    """Database and embedder, opened on the first search and checked once.

    Lazy so the server starts and lists its tools even when Postgres or Ollama
    is down; the search then explains which one to start.
    """

    _client: Any = field(default=None, init=False)
    _checked: bool = field(default=False, init=False)

    def search(self, question: str, k: int, as_of: date) -> list[Passage]:
        import httpx
        import psycopg

        from rb_errata import config, recall
        from rb_errata.ollama import Ollama, PinError, checked_digest
        from rb_errata.retrieve.methods import retrieve

        settings = config.load()
        try:
            if self._client is None:
                self._client = Ollama(settings)
            if not self._checked:
                checked_digest(self._client, settings.embed_model, settings.embed_digest)
                if recall._db_corpus(settings) != recall._manifest_corpus():
                    raise ToolError("the database differs from data/corpus.json; run `make ingest`")
                self._checked = True
            return retrieve(SEARCH_METHOD, settings, self._client, question, k, as_of)
        except PinError as e:
            raise ToolError(f"embedder check failed: {e}") from None
        except psycopg.OperationalError:
            raise ToolError("database unreachable; run `make db-up`") from None
        except httpx.TransportError:
            raise ToolError("Ollama unreachable; start Ollama, then retry") from None


def search_rules(question: str, as_of: str | None, k: int, search: Search) -> dict[str, Any]:
    if not question.strip():
        raise ToolError("question: empty")
    if not 1 <= k <= K_MAX:
        raise ToolError(f"k: between 1 and {K_MAX}")
    day = _date(as_of)
    in_effect = next(w for w in windows().values() if w.valid_from <= day
                     and (w.valid_to is None or day < w.valid_to))  # fmt: skip
    passages = search(question, k, day)
    return {
        "as_of": day.isoformat(),
        "version_in_effect": in_effect.version,
        "method": SEARCH_METHOD,
        "passages": [
            {
                "ref": p.source_ref,
                "rules": sorted(p.qualified_refs),
                **_window_fields(p.document.split("@", 1)[1]),
                "text": p.text,
            }
            for p in passages
        ],
    }
