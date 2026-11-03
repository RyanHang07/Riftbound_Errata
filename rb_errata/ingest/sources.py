"""Every Core Rules version: where it comes from and which bytes it must be.

The list itself is data/sources.yaml (slice 18), so a new version is an
appended entry written by `make add-version`, never a code change. This
module loads it once and refuses a registry that could ingest the wrong
thing: an unpinned or malformed hash, a duplicate, or versions out of order
(validity windows are derived from the order, A16).

Scope: Core Rules only. Tournament Rules, cards, errata and FAQs come later.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

REGISTRY = Path("data/sources.yaml")
CDN = "https://cmsassets.rgpub.io/sanity/files/dsfx7636/news_live"
MIRROR_REPO = "https://github.com/ChristianIvicevic/riftboundfaq"
MIRROR_RAW = "https://raw.githubusercontent.com/ChristianIvicevic/riftboundfaq"
PROVENANCE = ("cdn-verified", "mirror-only-unverified")
_SHA1 = re.compile(r"^[0-9a-f]{40}$")


@dataclass(frozen=True)
class RulesDoc:
    doc: str  # document family, used in source_ref: "core@1.4:315.2"
    version: str
    sha1: str
    urls: tuple[str, ...]  # tried in order; the first that hashes correctly wins
    # The announcement that states when this version took effect (A16). None
    # means no announcement exists, so the effective date is unknown and the
    # version is refused at ingestion rather than dated by guesswork.
    patch_notes: str | None
    # How the bytes were verified, recorded in the manifest.
    provenance: str
    name: str = ""  # the set it shipped with: "Vendetta"

    @property
    def id(self) -> str:
        return f"{self.doc}@{self.version}"

    @property
    def filename(self) -> str:
        return f"{self.doc}-rules-v{self.version}.pdf"


def vkey(version: str) -> tuple[int, ...]:
    return tuple(int(x) for x in version.split("."))


def parse(rows: list[dict[str, Any]]) -> tuple[RulesDoc, ...]:
    """Registry rows to documents, refusing anything that could mis-ingest. Pure."""
    docs = []
    for r in rows:
        v = str(r["version"])
        if not re.fullmatch(r"\d+\.\d+", v):
            raise ValueError(f"version {v!r}: expected MAJOR.MINOR")
        if not _SHA1.match(str(r["sha1"])):
            raise ValueError(f"{v}: sha1 must be 40 lowercase hex characters")
        if r["provenance"] not in PROVENANCE:
            raise ValueError(f"{v}: provenance must be one of {PROVENANCE}")
        if not r["urls"]:
            raise ValueError(f"{v}: no urls")
        docs.append(
            RulesDoc("core", v, r["sha1"], tuple(r["urls"]), r.get("patch_notes"),
                     r["provenance"], str(r.get("name") or ""))
        )  # fmt: skip
    versions = [d.version for d in docs]
    if len(set(versions)) != len(versions):
        raise ValueError(f"duplicate versions in the registry: {versions}")
    if versions != sorted(versions, key=vkey):
        raise ValueError(f"registry out of order: {versions}")
    return tuple(docs)


def load(path: Path = REGISTRY) -> tuple[RulesDoc, ...]:
    return parse(yaml.safe_load(path.read_text()))


CORE_RULES: tuple[RulesDoc, ...] = load()
