"""Slice 17 contracts: the API calls the MCP tools' functions and maps errors."""

from __future__ import annotations

from datetime import date
from typing import Any

from starlette.testclient import TestClient

from rb_errata import app, tools
from rb_errata.retrieve.vector import Passage

P = Passage("core@1.4:419.4", ["419.4", "419.4.b"], "text", 0.2, date(2026, 7, 24), None, "h")


class FakeBackend(tools.AgentBackend):
    def search(self, question: str, k: int, as_of: date) -> list[Passage]:
        return [P][:k]

    def ask(self, question: str, as_of: date) -> tuple[Any, Any]:
        state = {"answer": "Yes [core@1.4:419.4.b].", "confidence": None, "attempts": 0,
                 "warnings": [], "passages": [P]}  # fmt: skip
        return state, None


client = TestClient(app.build(FakeBackend()))


def test_versions_and_search_and_ask() -> None:
    assert client.get("/api/versions").json()["document"] == "Riftbound Core Rules"
    r = client.post("/api/search", json={"question": "q", "as_of": "2026-10-01"})
    assert r.status_code == 200 and r.json()["passages"][0]["ref"] == "core@1.4:419.4"
    a = client.post("/api/ask", json={"question": "q"}).json()
    assert a["citations"] == ["core@1.4:419.4.b"] and a["confidence"] is None


def test_tool_errors_become_400_with_the_fix() -> None:
    r = client.post("/api/search", json={"question": "q", "as_of": "2020-01-01"})
    assert r.status_code == 400 and "before 2025-10-24" in r.json()["error"]
    r = client.get("/api/rule", params={"ref": "nonsense"})
    assert r.status_code == 400 and "core@1.4:419.4.a" in r.json()["error"]
    r = client.get("/api/changed", params={"from": "1.4", "to": "1.3"})
    assert r.status_code == 400 and "must be older" in r.json()["error"]


def test_bad_bodies_are_400_not_500() -> None:
    assert client.post("/api/search", content=b"not json").status_code == 400
    assert client.post("/api/search", json={"question": "q", "k": "five"}).status_code == 400


def test_unexpected_errors_name_no_internals() -> None:
    class Broken(FakeBackend):
        def search(self, question: str, k: int, as_of: date) -> list[Passage]:
            raise RuntimeError("secret internals")

    r = TestClient(app.build(Broken())).post("/api/search", json={"question": "q"})
    assert r.status_code == 500 and "secret" not in r.text
