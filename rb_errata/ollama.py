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


class Ollama:
    def __init__(self, settings: Settings, transport: httpx.BaseTransport | None = None) -> None:
        self._s = settings
        self._http = httpx.Client(
            base_url=settings.ollama_url, timeout=settings.http_timeout_s, transport=transport
        )

    def close(self) -> None:
        self._http.close()

    def _post(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        r = self._http.post(path, json=body)
        r.raise_for_status()
        data: dict[str, Any] = r.json()
        return data

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
            },
        )
        embeddings: list[list[float]] = data["embeddings"]
        return embeddings

    def generate(self, prompt: str, *, max_tokens: int) -> Generation:
        data = self._post(
            "/api/generate",
            {
                "model": self._s.gen_model,
                "prompt": prompt,
                "stream": False,
                "think": self._s.gen_think,
                "options": {
                    "temperature": self._s.gen_temperature,
                    "seed": self._s.gen_seed,
                    "num_ctx": self._s.gen_num_ctx,
                    "num_predict": max_tokens,
                },
            },
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
