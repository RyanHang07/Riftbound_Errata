"""Found on the first full answers run: Ollama dropped a connection mid-run.
Dropped requests are retried and counted; a never-connected client fails fast."""

from __future__ import annotations

from typing import cast

import httpx
import pytest

from rb_errata.config import Settings
from rb_errata.ollama import Ollama

OK = {"response": "fine", "prompt_eval_count": 1, "eval_count": 1, "done_reason": "stop"}


def client_with(failures: list[Exception], monkeypatch: pytest.MonkeyPatch) -> Ollama:
    monkeypatch.setattr(Ollama, "RETRY_WAITS_S", (0.0, 0.0, 0.0))
    queue = list(failures)

    def handler(request: httpx.Request) -> httpx.Response:
        if queue:
            raise queue.pop(0)
        return httpx.Response(200, json=OK)

    return Ollama(Settings(), transport=httpx.MockTransport(handler))


def test_dropped_connection_mid_run_is_retried_and_counted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    c = client_with([], monkeypatch)
    c.generate("warm up", max_tokens=5)  # the session has connected
    c2 = client_with([httpx.RemoteProtocolError("Server disconnected")], monkeypatch)
    assert c2.generate("q", max_tokens=5).text == "fine" and c2.retries == 1
    assert c.retries == 0


def test_never_connected_fails_at_once(monkeypatch: pytest.MonkeyPatch) -> None:
    c = client_with([httpx.ConnectError("refused")], monkeypatch)
    with pytest.raises(httpx.ConnectError):
        c.generate("q", max_tokens=5)
    assert c.retries == 0  # "Ollama unreachable" stays fast for doctor and the tools


def test_lost_connection_after_success_is_retried(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 2:
            raise httpx.ConnectError("runner restarting")
        return httpx.Response(200, json=OK)

    monkeypatch.setattr(Ollama, "RETRY_WAITS_S", (0.0, 0.0, 0.0))
    c = Ollama(Settings(), transport=httpx.MockTransport(handler))
    c.generate("first", max_tokens=5)
    assert c.generate("second", max_tokens=5).text == "fine" and c.retries == 1


def test_gives_up_after_the_last_wait(monkeypatch: pytest.MonkeyPatch) -> None:
    errors: list[Exception] = [httpx.RemoteProtocolError("x") for _ in range(4)]
    c = client_with(errors, monkeypatch)
    with pytest.raises(httpx.RemoteProtocolError):
        c.generate("q", max_tokens=5)
    assert c.retries == 3


def test_hung_generation_times_out_and_is_retried(monkeypatch: pytest.MonkeyPatch) -> None:
    # Found at question ~140 of the first full run: a request hung silently.
    seen: list[float] = []
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        seen.append(request.extensions["timeout"]["read"])
        if calls["n"] == 2:
            raise httpx.ReadTimeout("stuck")
        return httpx.Response(200, json=OK)

    monkeypatch.setattr(Ollama, "RETRY_WAITS_S", (0.0, 0.0, 0.0))
    s = Settings()
    c = Ollama(s, transport=httpx.MockTransport(handler))
    c.generate("first", max_tokens=5)  # cold: the long timeout
    assert c.generate("second", max_tokens=5).text == "fine" and c.retries == 1
    assert seen[0] == s.http_timeout_s and seen[1] == seen[2] == s.gen_timeout_s


def test_hung_embedding_is_retried_too(monkeypatch: pytest.MonkeyPatch) -> None:
    # The second hang (question ~210) could be the search's embedding call.
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 2:
            raise httpx.ReadTimeout("stuck")
        return httpx.Response(200, json={"embeddings": [[0.0]]})

    monkeypatch.setattr(Ollama, "RETRY_WAITS_S", (0.0, 0.0, 0.0))
    c = Ollama(Settings(), transport=httpx.MockTransport(handler))
    c.embed(["first"])
    assert c.embed(["second"]) == [[0.0]] and c.retries == 1


def test_database_retries_only_after_a_first_connection(monkeypatch: pytest.MonkeyPatch) -> None:
    import psycopg

    from rb_errata import db

    calls = {"n": 0}
    sentinel = object()

    def fake_connect(*_: object, **__: object) -> object:
        calls["n"] += 1
        if calls["n"] in (1, 3):
            raise psycopg.OperationalError("connection timeout expired")
        return sentinel

    monkeypatch.setattr(db, "RETRY_WAITS_S", (0.0, 0.0, 0.0))
    monkeypatch.setattr(db, "_reached", False)
    monkeypatch.setattr(psycopg, "connect", fake_connect)
    with pytest.raises(psycopg.OperationalError):
        db.connect(Settings())  # never reached: fails at once (doctor stays fast)
    assert calls["n"] == 1
    assert cast(object, db.connect(Settings())) is sentinel  # reached now
    assert cast(object, db.connect(Settings())) is sentinel  # call 3 failed, was retried
    assert calls["n"] == 4


def test_warmup_primes_the_cache_with_the_identical_request() -> None:
    """A59: one 1-token request with the same prompt and options first, so the
    measured request always starts with its prompt cached (A56)."""
    import json

    seen: list[dict[str, object]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(json.loads(request.content))
        n = len(seen)
        return httpx.Response(200, json={**OK, "prompt_eval_count": 900 if n == 1 else 1,
                                         "prompt_eval_duration": 10 if n == 1 else 2})  # fmt: skip

    g = Ollama(Settings(), transport=httpx.MockTransport(handler)).generate("q", max_tokens=50)
    warm, real = seen
    opts_w, opts_r = (
        cast(dict[str, object], warm["options"]),
        cast(dict[str, object], real["options"]),
    )
    assert (opts_w["num_predict"], opts_r["num_predict"]) == (1, 50)
    assert {**opts_w, "num_predict": 50} == opts_r and warm["prompt"] == real["prompt"]
    # the prompt's size and read time include the warm-up, so doctor's rate holds
    assert (g.prompt_tokens, g.prompt_ns) == (901, 12)


def test_warmup_off_sends_one_request() -> None:
    from dataclasses import replace

    n = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal n
        n += 1
        return httpx.Response(200, json=OK)

    Ollama(replace(Settings(), gen_warmup=False), transport=httpx.MockTransport(handler)).generate(
        "q", max_tokens=5
    )
    assert n == 1
