"""Slice 15 contracts: each MCP tool's errors, and the server over a real pipe.

The PDFs are not in CI (data/raw/ is gitignored), so rule text comes from a
fake loader with made-up rules; windows come from the committed corpus.
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path
from typing import Any

import anyio
import pytest
from mcp.server.mcpserver.exceptions import ToolError

from rb_errata import tools
from rb_errata.ingest.rules import Rule
from rb_errata.retrieve.vector import Passage

RULES = {
    "1.3": {
        "100": Rule("100", "Players may draw a card at the start of the turn."),
        "200": Rule("200", "A unit with Tank must be assigned damage first."),
        "300": Rule("300", "This rule was removed in the next version entirely."),
    },
    "1.4": {
        "100": Rule("100", "Players must draw a card at the start of the turn."),
        "201": Rule("201", "A unit with Tank must be assigned damage first."),
        "400": Rule("400", "Brand new wording about a mechanic nobody had before."),
    },
}


def load(v: str) -> dict[str, Rule]:
    return RULES[v]


def raises(match: str) -> Any:
    return pytest.raises(ToolError, match=match)


# --- refs and dates ------------------------------------------------------------


@pytest.mark.parametrize(
    ("ref", "match"),
    [
        ("419.4.a", "not a rule reference"),
        ("core@1.4", "not a rule reference"),
        ("cards@1.4:100", "only the Core Rules"),
        ("core@1.0:100", "no known effective date"),
        ("core@9.9:100", "unknown version"),
    ],
)
def test_bad_refs_say_why(ref: str, match: str) -> None:
    with raises(match):
        tools.parse_ref(ref)


def test_ref_accepts_a_v_prefix() -> None:
    assert tools.parse_ref(" core@v1.4:419.4.a ") == ("1.4", "419.4.a")


# --- search_rules --------------------------------------------------------------


def passage(ref: str, valid_from: str, valid_to: str | None) -> Passage:
    end = date.fromisoformat(valid_to) if valid_to else None
    refs = [ref.split(":", 1)[1]]
    return Passage(ref, refs, "text", 0.1, date.fromisoformat(valid_from), end, "sha256:x")


def fake_search(question: str, k: int, as_of: date) -> list[Passage]:
    return [passage("core@1.3:419.4", "2026-03-30", "2026-07-24")][:k]


@pytest.mark.parametrize(
    ("question", "as_of", "k", "match"),
    [
        ("  ", None, 5, "question: empty"),
        ("q", None, 0, "k: between 1 and 20"),
        ("q", None, 21, "k: between 1 and 20"),
        ("q", "1 May 2026", 5, "not a date"),
        ("q", "2025-10-23", 5, "before 2025-10-24"),
    ],
)
def test_search_refuses_bad_input(question: str, as_of: str | None, k: int, match: str) -> None:
    with raises(match):
        tools.search_rules(question, as_of, k, fake_search)


def test_search_reports_version_and_staleness() -> None:
    out = tools.search_rules("q", "2026-05-01", 5, fake_search)
    assert (out["as_of"], out["version_in_effect"], out["method"]) == ("2026-05-01", "1.3", "as-of")
    p = out["passages"][0]
    assert p["rules"] == ["core@1.3:419.4"]
    assert (p["valid_to"], p["newer_version_exists"]) == ("2026-07-24", True)


def test_search_boundary_day_is_the_new_version() -> None:
    # Half-open windows: on the day v1.4 takes effect, v1.3 is already out.
    assert tools.search_rules("q", "2026-07-24", 5, fake_search)["version_in_effect"] == "1.4"


# --- get_rule ------------------------------------------------------------------


def test_get_rule_returns_text_and_window() -> None:
    out = tools.get_rule("core@1.4:100", load)
    assert out["text"].startswith("Players must")
    assert (out["valid_from"], out["valid_to"]) == ("2026-07-24", None)


def test_get_rule_unknown_number() -> None:
    with raises("core@1.4 has no rule 999"):
        tools.get_rule("core@1.4:999", load)


def test_missing_or_altered_pdf_is_refused(tmp_path: Path) -> None:
    with raises("missing; run `make fetch`"):
        tools.rules.__wrapped__("1.4", tmp_path)
    (tmp_path / "core-rules-v1.4.pdf").write_bytes(b"not the pinned bytes")
    with raises("does not match its pinned SHA-1"):
        tools.rules.__wrapped__("1.4", tmp_path)


# --- list_versions -------------------------------------------------------------


def test_list_versions_marks_refused_and_basis() -> None:
    rows = {r["version"]: r for r in tools.list_versions()["versions"]}
    assert rows["1.0"]["searchable"] is False and rows["1.0"]["reason"]
    assert rows["1.4"]["searchable"] is True and rows["1.4"]["valid_to"] is None
    assert rows["1.1"]["date_basis"] == "announcement-date"


# --- what_changed --------------------------------------------------------------


@pytest.mark.parametrize(
    ("args", "match"),
    [
        (("1.4", "1.3", None), "must be older"),
        (("1.3", "1.3", None), "must be older"),
        (("1.2", "1.3", "core@1.4:100"), "not v1.2 or v1.3"),
        (("1.3", "1.4", "core@1.4:999"), "has no rule 999"),
        (("1.0", "1.4", None), "no known effective date"),
    ],
)
def test_what_changed_refuses_bad_input(args: tuple[str, str, str | None], match: str) -> None:
    with raises(match):
        tools.what_changed(*args, load=load)


@pytest.mark.parametrize(
    ("ref", "status", "other"),
    [
        ("core@1.4:100", "changed", "core@1.3:100"),  # may -> must, same number
        ("core@1.4:201", "renumbered", "core@1.3:200"),  # found by wording, not number
        ("core@1.3:200", "renumbered", "core@1.4:201"),
        ("core@1.4:400", "added", None),
        ("core@1.3:300", "removed", None),
    ],
)
def test_what_changed_one_rule(ref: str, status: str, other: str | None) -> None:
    out = tools.what_changed("1.3", "1.4", ref, load=load)
    assert out["status"] == status
    sides = [s["ref"] if s else None for s in (out["old"], out["new"])]
    assert ref in sides and other in sides


def test_what_changed_summary() -> None:
    out = tools.what_changed("1.3", "1.4", load=load)
    assert out["counts"] == {"changed": 1, "added": 1, "removed": 1}
    assert out["added"] == ["core@1.4:400"] and out["removed"] == ["core@1.3:300"]


# --- the backend's failures become messages the user can act on ---------------


@pytest.mark.parametrize(
    ("error", "match"),
    [
        ("psycopg", "database unreachable; run `make db-up`"),
        ("httpx", "Ollama unreachable"),
        ("pin", "embedder check failed"),
    ],
)
def test_backend_errors_are_actionable(
    monkeypatch: pytest.MonkeyPatch, error: str, match: str
) -> None:
    import httpx
    import psycopg

    from rb_errata.ollama import PinError
    from rb_errata.retrieve import methods

    exc = {
        "psycopg": psycopg.OperationalError("down"),
        "httpx": httpx.ConnectError("down"),
        "pin": PinError("mismatch"),
    }[error]

    def boom(*_: Any, **__: Any) -> Any:
        raise exc

    monkeypatch.setattr(methods, "retrieve", boom)
    backend = tools.Backend()
    backend._client, backend._checked = object(), True  # skip the one-time checks
    with raises(match):
        backend.search("q", 5, date(2026, 5, 1))


# --- the server ----------------------------------------------------------------


def test_server_lists_four_read_only_tools_and_returns_errors() -> None:
    from mcp import Client

    from rb_errata.server import server

    async def go() -> tuple[list[Any], Any]:
        async with Client(server) as c:
            listed = (await c.list_tools()).tools
            return listed, await c.call_tool("get_rule", {"ref": "nonsense"})

    listed, bad = anyio.run(go)
    assert sorted(t.name for t in listed) == [
        "get_rule",
        "list_versions",
        "search_rules",
        "what_changed",
    ]
    assert all(t.annotations and t.annotations.read_only_hint for t in listed)
    assert bad.is_error and "not a rule reference" in bad.content[0].text


def test_server_speaks_clean_stdio() -> None:
    # Claude Desktop's transport: a stray print to stdout would corrupt the
    # JSON-RPC stream before any tool is listed.
    from mcp import Client
    from mcp.client.stdio import StdioServerParameters

    params = StdioServerParameters(command=sys.executable, args=["-m", "rb_errata.server"])

    async def go() -> dict[str, Any]:
        async with Client(params) as c:
            res = await c.call_tool("list_versions", {})
            return res.structured_content or {}

    assert [v["version"] for v in anyio.run(go)["versions"]][-1] == "1.4"
