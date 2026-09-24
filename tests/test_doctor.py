"""Contract tests for doctor, against a fake Ollama. Free, seconds, no model.

These pin down the judgements doctor makes, so that when it runs against a
real Ollama the only unknowns are the real ones.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

import httpx
import pytest

from rb_errata import config, doctor
from rb_errata.config import Settings
from rb_errata.doctor import Status
from rb_errata.ollama import Generation, Ollama

EMBED_DIGEST = "a" * 64
GEN_DIGEST = "b" * 64


def fake_ollama(
    *,
    version: str = "0.12.0",
    dims: int = 768,
    thinking: str = "",
    models: list[str] | None = None,
) -> Callable[[Settings], Ollama]:
    tags = models if models is not None else ["nomic-embed-text:latest", "qwen3:4b"]
    digests = {"nomic-embed-text:latest": EMBED_DIGEST, "qwen3:4b": f"sha256:{GEN_DIGEST}"}

    def handle(req: httpx.Request) -> httpx.Response:
        body: dict[str, Any] = json.loads(req.content) if req.content else {}
        match req.url.path:
            case "/api/version":
                return httpx.Response(200, json={"version": version})
            case "/api/tags":
                return httpx.Response(
                    200, json={"models": [{"name": t, "digest": digests[t]} for t in tags]}
                )
            case "/api/ps":
                return httpx.Response(
                    200, json={"models": [{"name": "qwen3:4b", "size": 100, "size_vram": 0}]}
                )
            case "/api/embed":
                assert body["truncate"] is False
                return httpx.Response(200, json={"embeddings": [[0.1] * dims]})
            case "/api/generate":
                assert body["think"] is False and body["options"]["num_ctx"] == 8192
                long = len(body["prompt"]) > 1000
                return httpx.Response(
                    200,
                    json={
                        "response": "OK" if not long else "Rule 1.0 says...",
                        "thinking": thinking,
                        "prompt_eval_count": 3000 if long else 12,
                        "prompt_eval_duration": 30_000_000_000,  # 30 s -> 100 tok/s
                        "eval_count": 180 if long else 1,
                        "eval_duration": 18_000_000_000,  # 18 s -> 10 tok/s
                        "load_duration": 2_000_000_000,
                        "done_reason": "length",
                    },
                )
        return httpx.Response(404)

    return lambda s: Ollama(s, transport=httpx.MockTransport(handle))


def pinned(**extra: str) -> Settings:
    return config.load({"RB_EMBED_DIGEST": EMBED_DIGEST, "RB_GEN_DIGEST": GEN_DIGEST, **extra})


@pytest.fixture(autouse=True)
def healthy_database(monkeypatch: pytest.MonkeyPatch) -> None:
    ok = doctor.Check("database", Status.PASS, "fake")
    monkeypatch.setattr(doctor, "check_database", lambda _s: ok)


def by_name(checks: list[doctor.Check]) -> dict[str, doctor.Check]:
    return {c.name: c for c in checks}


def test_all_green_and_budget_uses_measured_rates() -> None:
    checks = doctor.run(pinned(), fake_ollama())
    assert doctor.exit_code(checks) == 0, doctor.render(checks, "test")
    # 3000/100 + 180/10 = 48 s/answer; x100 q = 1.33 h/config; x6 = 8.0 h.
    detail = by_name(checks)["budget"].detail
    assert "48.0s/answer" in detail and "8.0 h total" in detail and "ASSUMED" in detail


def test_unpinned_model_fails_and_prints_the_observed_digest() -> None:
    checks = by_name(doctor.run(config.load({}), fake_ollama()))
    assert checks["embed pin"].status is Status.FAIL
    assert EMBED_DIGEST in checks["embed pin"].detail
    # The functional check still runs, so one doctor run shows everything.
    assert checks["embed model"].status is Status.PASS


def test_repushed_tag_fails_the_pin() -> None:
    checks = by_name(doctor.run(pinned(RB_GEN_DIGEST="c" * 64), fake_ollama()))
    assert checks["generation pin"].status is Status.FAIL


def test_wrong_dimension_fails() -> None:
    checks = by_name(doctor.run(pinned(), fake_ollama(dims=1024)))
    assert checks["embed model"].status is Status.FAIL


def test_ignored_think_flag_fails() -> None:
    checks = by_name(doctor.run(pinned(), fake_ollama(thinking="let me reason...")))
    assert checks["generation model"].status is Status.FAIL
    assert checks["budget"].status is Status.UNKNOWN


def test_old_ollama_fails_and_downstream_is_unknown_not_fail() -> None:
    checks = doctor.run(pinned(), fake_ollama(version="0.5.7"))
    named = by_name(checks)
    assert named["ollama"].status is Status.FAIL
    assert named["generation model"].status is Status.UNKNOWN


def test_missing_model_fails_function_and_leaves_pin_unknown() -> None:
    checks = by_name(doctor.run(pinned(), fake_ollama(models=["nomic-embed-text:latest"])))
    assert checks["generation model"].status is Status.FAIL
    assert checks["generation pin"].status is Status.UNKNOWN


def test_unreachable_ollama_is_a_fail_not_a_crash() -> None:
    def refuse(req: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused", request=req)

    checks = doctor.run(pinned(), lambda s: Ollama(s, transport=httpx.MockTransport(refuse)))
    assert by_name(checks)["ollama"].status is Status.FAIL


def _gen(prompt_tokens: int, answer_tokens: int) -> Generation:
    return Generation("x", "", prompt_tokens, 10**9, answer_tokens, 10**9, 0, "stop")


def test_filled_context_is_a_fail_because_the_prompt_may_be_truncated() -> None:
    check, tp = doctor.judge_generation(pinned(), _gen(10, 1), _gen(8100, 180), 0.0)
    assert check.status is Status.FAIL and tp is None


def test_too_little_work_to_time_is_unknown_not_pass() -> None:
    # A cached prefix makes prefill look instant. That is not a measurement.
    check, _ = doctor.judge_generation(pinned(), _gen(10, 1), _gen(20, 180), 0.0)
    assert check.status is Status.UNKNOWN


def test_exit_codes_keep_three_states_apart() -> None:
    c = doctor.Check
    assert doctor.exit_code([c("a", Status.PASS, "")]) == 0
    assert doctor.exit_code([c("a", Status.UNKNOWN, ""), c("b", Status.FAIL, "")]) == 1
    assert doctor.exit_code([c("a", Status.PASS, ""), c("b", Status.UNKNOWN, "")]) == 2


def test_probe_prompt_starts_with_nonce_to_defeat_prefix_cache() -> None:
    a = doctor.throughput_probe_prompt(pinned(), "111")
    b = doctor.throughput_probe_prompt(pinned(), "222")
    assert a[:12] != b[:12]
    assert "<retrieved_passages>" in a
