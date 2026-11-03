"""Found on the first full answers run: Ollama dropped a connection mid-run.
Dropped requests are retried and counted; a never-connected client fails fast."""

from __future__ import annotations

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
