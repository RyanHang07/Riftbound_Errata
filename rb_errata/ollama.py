"""Thin HTTP client for the Ollama endpoints we use.

Shared by embedding (ingest and retrieve) and generation, so it sits at the
package root rather than under either. Every request states its options
explicitly; nothing relies on an Ollama default that could change between
Ollama releases.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from rb_errata.config import Settings


@dataclass(frozen=True)
class LocalModel:
    name: str
    digest: str
    size_bytes: int


@dataclass(frozen=True)
class Generation:
    text: str
    thinking: str
    prompt_tokens: int
    prompt_ns: int
    answer_tokens: int
    answer_ns: int
    load_ns: int
    done_reason: str


def normalise_digest(digest: str) -> str:
    # Ollama reports bare hex in some places and "sha256:<hex>" in others.
    # Comparing them unnormalised would fail a correctly pinned model.
    return digest.strip().lower().removeprefix("sha256:")


def _with_latest(name: str) -> str:
    # `ollama pull nomic-embed-text` is stored as "nomic-embed-text:latest".
    return name if ":" in name else f"{name}:latest"


class PinError(RuntimeError):
    pass


def checked_digest(client: Ollama, tag: str, pinned: str) -> str:
    """The local digest of `tag`, refusing an absent, unpinned or mismatched model.

    The rule doctor checks, enforced again wherever a model's output is
    recorded: vectors in the database, answers in a committed fixture.
    """
    found = client.find(tag)
    if found is None:
        raise PinError(f"{tag} not pulled: `ollama pull {tag}`")
    if not pinned or found.digest != normalise_digest(pinned):
        raise PinError(f"{tag} digest unpinned or mismatched: run `make doctor`")
    return found.digest


class Ollama:
    # Found on the first full answers run (slice 11): Ollama dropped a connection
    # mid-run ("Server disconnected without sending a response") and the whole
    # run died. Ollama restarts a crashed model runner on the next request, so
    # a dropped connection is retried after a pause; every retry is counted
    # and recorded with the run, never hidden.
    RETRY_WAITS_S: tuple[float, ...] = (5.0, 20.0, 60.0)

    def __init__(self, settings: Settings, transport: httpx.BaseTransport | None = None) -> None:
        self._s = settings
        self._http = httpx.Client(
            base_url=settings.ollama_url, timeout=settings.http_timeout_s, transport=transport
        )
        self.retries = 0
        self._connected = False  # set by the first successful request

    def close(self) -> None:
        self._http.close()

    def _placement(self) -> dict[str, Any]:
        # num_gpu is the number of model layers offloaded to the GPU. Zero
        # keeps the whole model on the CPU; omitting it lets Ollama decide.
        return {"num_gpu": 0} if self._s.cpu_only else {}

    def _post(
        self, path: str, body: dict[str, Any], timeout: float | None = None
    ) -> dict[str, Any]:
        import sys
        import time

        for wait in (*self.RETRY_WAITS_S, None):
            try:
                r = self._http.post(path, json=body, timeout=timeout or self._s.http_timeout_s)
                r.raise_for_status()
                data: dict[str, Any] = r.json()
                self._connected = True
                return data
            except (
                httpx.RemoteProtocolError, httpx.ReadError, httpx.ConnectError, httpx.ReadTimeout
            ) as exc:  # fmt: skip
                # A session that never connected fails at once, so doctor and
                # the tools still report "Ollama unreachable" in seconds; a
                # connection lost mid-run (the runner restarting) is retried.
                if wait is None or (isinstance(exc, httpx.ConnectError) and not self._connected):
                    raise
                self.retries += 1
                print(f"  Ollama dropped the request ({type(exc).__name__}); retrying in "
                      f"{wait:.0f} s", file=sys.stderr, flush=True)  # fmt: skip
                time.sleep(wait)
        raise AssertionError("unreachable")

    def version(self) -> str:
        r = self._http.get("/api/version")
        r.raise_for_status()
        return str(r.json()["version"])

    def local_models(self) -> dict[str, LocalModel]:
        r = self._http.get("/api/tags")
        r.raise_for_status()
        out: dict[str, LocalModel] = {}
        for m in r.json().get("models", []):
            name = _with_latest(str(m["name"]))
            out[name] = LocalModel(name, normalise_digest(str(m["digest"])), int(m.get("size", 0)))
        return out

    def find(self, name: str) -> LocalModel | None:
        return self.local_models().get(_with_latest(name))

    def loaded_vram_fraction(self, name: str) -> float | None:
        """Share of the loaded model held in GPU memory; None if not loaded.

        The target is CPU only. A throughput figure measured with GPU offload
        describes a different machine, so doctor reports this next to it.
        """
        r = self._http.get("/api/ps")
        r.raise_for_status()
        for m in r.json().get("models", []):
            if _with_latest(str(m["name"])) == _with_latest(name):
                size = int(m.get("size", 0))
                return int(m.get("size_vram", 0)) / size if size else 0.0
        return None

    def embed(self, texts: list[str]) -> list[list[float]]:
        data = self._post(
            "/api/embed",
            {
                "model": self._s.embed_model,
                "input": texts,
                # Default is to silently cut an over-long input to the model's
                # context and embed only its beginning. A chunk whose vector
                # ignores its second half is a retrieval miss nobody can see.
                "truncate": False,
                "options": self._placement(),
            },
        )
        embeddings: list[list[float]] = data["embeddings"]
        return embeddings

    def generate(
        self, prompt: str, *, max_tokens: int, model: str | None = None, json_mode: bool = False
    ) -> Generation:
        # `model` lets the judge (slice 11) use a different pinned model with
        # identical settings; json_mode asks Ollama to constrain output to JSON,
        # so a verdict is parsed, never pattern-matched out of prose.
        extra: dict[str, Any] = {"format": "json"} if json_mode else {}
        data = self._post(
            "/api/generate",
            {
                "model": model or self._s.gen_model,
                "prompt": prompt,
                "stream": False,
                "think": self._s.gen_think,
                **extra,
                "options": {
                    "temperature": self._s.gen_temperature,
                    "seed": self._s.gen_seed,
                    "num_ctx": self._s.gen_num_ctx,
                    "num_predict": max_tokens,
                    **self._placement(),
                },
            },
            # The first request of a session may include loading a model from
            # disk: it gets the long timeout. After that, gen_timeout_s (still
            # room for a cold load of a second model) separates slow from stuck.
            timeout=self._s.gen_timeout_s if self._connected else None,
        )
        return Generation(
            text=str(data.get("response", "")),
            thinking=str(data.get("thinking", "") or ""),
            prompt_tokens=int(data.get("prompt_eval_count", 0)),
            prompt_ns=int(data.get("prompt_eval_duration", 0)),
            answer_tokens=int(data.get("eval_count", 0)),
            answer_ns=int(data.get("eval_duration", 0)),
            load_ns=int(data.get("load_duration", 0)),
            done_reason=str(data.get("done_reason", "")),
        )
