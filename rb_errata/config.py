"""Every setting, in one place, each overridable by an RB_* environment variable.

Settings that change what a vector or an answer *means* (model tags, digests,
prefixes, think, num_ctx, seed) live here rather than at call sites, so that a
run can record the whole set and two runs can be compared field by field.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import asdict, dataclass, fields
from typing import Any


@dataclass(frozen=True)
class Settings:
    database_url: str = "postgresql://rb_errata:rb_errata@localhost:5433/rb_errata"
    ollama_url: str = "http://localhost:11434"

    # --- Embedding -------------------------------------------------------
    # Changing any of these four changes what every stored vector means,
    # silently. Treat a change as a new corpus, not an upgrade.
    embed_model: str = "nomic-embed-text"
    # Empty means "not pinned yet". doctor fails on an empty pin rather than
    # passing, and prints the observed digest so it can be pasted in.
    embed_digest: str = "0a109f422b47e3a30ba2b10eca18548e944e8a23073ee3f3e947efcf3c45e59f"
    embed_dims: int = 768
    # nomic-embed-text was trained with task prefixes. Without them retrieval
    # quality drops, and changing them later re-means every vector.
    embed_doc_prefix: str = "search_document: "
    embed_query_prefix: str = "search_query: "
    # Which embedder profile (EMBED_PROFILES) the fields above came from. Also
    # names the Postgres schema holding that profile's vectors (see db_schema).
    embed_profile: str = "nomic"

    # --- Hardware --------------------------------------------------------
    # Keeps both models off the GPU (Ollama's num_gpu=0). The brief targets a
    # 16 GB machine with no GPU; development machines often have one, and a
    # GPU figure in a budget describes hardware a judge may not own. Off for
    # day-to-day speed, on for any number that goes into a budget or writeup.
    cpu_only: bool = False

    # --- Generation ------------------------------------------------------
    # The instruct-only 2507 build, not plain "qwen3:4b". Found in the first
    # drift run (A18, A19): with think=false the plain tag still reasoned aloud
    # in its visible answer, ran out of tokens and never answered.
    gen_model: str = "qwen3:4b-instruct-2507-q4_K_M"
    gen_digest: str = ""
    # qwen3 emits a hidden reasoning trace by default. Off: it inflates token
    # counts, makes the time budget meaningless, and changes answers. Turning
    # it on later is an ablation to measure, not a default to drift into.
    gen_think: bool = False
    # Ollama's default context is small and it truncates an over-long prompt
    # WITHOUT an error, dropping retrieved passages from the front. Set it
    # explicitly and large enough for a full passage block plus the answer.
    gen_num_ctx: int = 8192
    gen_temperature: float = 0.0
    gen_seed: int = 42

    # --- Time budget -----------------------------------------------------
    # Assumptions, not measurements. doctor labels them as such and multiplies
    # them by the throughput it *does* measure.
    budget_questions: int = 100
    budget_configs: int = 6
    budget_prompt_tokens: int = 3000
    budget_answer_tokens: int = 180

    # Timed generations per doctor run; the budget uses the median.
    doctor_probe_runs: int = 3

    # --- Timeouts --------------------------------------------------------
    # A first call loads the model from disk; on a 16 GB CPU box that can take
    # tens of seconds, so a short timeout would report a healthy model as down.
    http_timeout_s: float = 600.0

    @property
    def db_schema(self) -> str:
        """Each embedder's chunks and cache live in their own Postgres schema.

        Slice 7 compares two embedders on the same questions. One shared table
        would mean re-ingesting to switch, destroying the vectors the other
        run was measured on; a schema per profile keeps both runnable. The
        default stays in `public`, so the database ingested before profiles
        existed is still the nomic corpus, untouched.
        """
        return "public" if self.embed_profile == "nomic" else f"emb_{self.embed_profile}"

    def as_record(self) -> dict[str, Any]:
        """Everything except credentials, for recording alongside a run."""
        record = asdict(self)
        record.pop("database_url")
        return record


def _coerce(raw: str, target: type[Any]) -> Any:
    if target is bool:
        lowered = raw.strip().lower()
        if lowered in {"1", "true", "yes", "on"}:
            return True
        if lowered in {"0", "false", "no", "off"}:
            return False
        # Refuse to guess: "ture" silently becoming False would flip `think`.
        raise ValueError(f"not a boolean: {raw!r}")
    return target(raw)


_TYPES: dict[str, type[Any]] = {"str": str, "int": int, "float": float, "bool": bool}


# The five settings that decide what a stored vector means travel together
# (A10): a model with another model's prefixes, dimension or digest pin is a
# silent mismatch, not an error. Digests are committed here, pinned (A3).
EMBED_PROFILES: dict[str, dict[str, Any]] = {
    "nomic": {
        "embed_model": "nomic-embed-text",
        "embed_digest": "0a109f422b47e3a30ba2b10eca18548e944e8a23073ee3f3e947efcf3c45e59f",
        "embed_dims": 768,
        "embed_doc_prefix": "search_document: ",
        "embed_query_prefix": "search_query: ",
    },
    # Slice 7 (A25). Qwen3-Embedding is trained with an instruction on the
    # query side only; documents are embedded as they are. The format follows
    # the model card: "Instruct: <task>\nQuery:<query>".
    "qwen3": {
        "embed_model": "qwen3-embedding:0.6b",
        # From the user's first `make doctor EMBED=qwen3`, 2026-10-02.
        "embed_digest": "ac6da0dfba84a81fdbfbaf330198c33cd77c4cdfc53e8bc50eb581914a15621d",
        "embed_dims": 1024,
        "embed_doc_prefix": "",
        "embed_query_prefix": (
            "Instruct: Given a question about the rules of a trading card game, "
            "retrieve the rule passages that answer it\nQuery:"
        ),
    },
}


def load(env: Mapping[str, str] | None = None) -> Settings:
    """Build Settings from RB_<FIELD> variables, falling back to defaults.

    RB_EMBED_PROFILE picks an embedder profile. A non-default profile sets all
    five embedding fields and ignores RB_EMBED_* overrides: a .env written for
    nomic pins nomic's digest, and applying it to another model would fail
    every pin check, or worse, pass one by accident.
    """
    env = os.environ if env is None else env
    profile = env.get("RB_EMBED_PROFILE", "nomic")
    if profile not in EMBED_PROFILES:
        raise ValueError(f"unknown embed profile {profile!r}; one of {sorted(EMBED_PROFILES)}")
    overrides: dict[str, Any] = {"embed_profile": profile}
    locked = set(EMBED_PROFILES[profile]) if profile != "nomic" else set()
    for f in fields(Settings):
        key = f"RB_{f.name.upper()}"
        if key in env and f.name not in locked and f.name != "embed_profile":
            # `from __future__ import annotations` makes f.type a string.
            overrides[f.name] = _coerce(env[key], _TYPES[str(f.type)])
    if profile != "nomic":
        overrides |= EMBED_PROFILES[profile]
    return Settings(**overrides)
