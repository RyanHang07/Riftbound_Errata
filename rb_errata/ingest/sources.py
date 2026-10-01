"""Every document slice 2 ingests: where it comes from and which bytes it must be.

Each PDF is pinned by SHA-1. Riot's CDN names files by the SHA-1 of their
bytes, so for an official URL the pin and the filename are the same fact, and
a mirror copy is accepted only if it hashes to the same value. A download that
does not match is refused, never ingested "close enough".

Scope: Core Rules only. Tournament Rules, cards, errata and FAQs come later.
"""

from __future__ import annotations

from dataclasses import dataclass

CDN = "https://cmsassets.rgpub.io/sanity/files/dsfx7636/news_live"
# Pinned to a commit, so the mirror cannot change underneath us either.
MIRROR = (
    "https://raw.githubusercontent.com/ChristianIvicevic/riftboundfaq/"
    "816d3b32d32a9966fc73367efb690fcbb4c195ca/sources"
)
NEWS = "https://playriftbound.com/en-us/news"


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
    # How the bytes were verified in slice 1, recorded in the manifest.
    provenance: str

    @property
    def id(self) -> str:
        return f"{self.doc}@{self.version}"

    @property
    def filename(self) -> str:
        return f"{self.doc}-rules-v{self.version}.pdf"


CORE_RULES: tuple[RulesDoc, ...] = (
    RulesDoc(
        "core",
        "1.0",
        "c780858c1621672aea0dc6b454e9233f5a43d000",
        (f"{CDN}/c780858c1621672aea0dc6b454e9233f5a43d000.pdf", f"{MIRROR}/CR-v1.0.pdf"),
        # The pre-release edition (June 2025) had no patch notes. With no
        # stated effective date it is refused; that is the A16 guard working.
        None,
        "cdn-verified",
    ),
    RulesDoc(
        "core",
        "1.1",
        "dbc96e31db9d0257b0791aafb6dbb0cd219d3efb",
        (f"{CDN}/dbc96e31db9d0257b0791aafb6dbb0cd219d3efb.pdf", f"{MIRROR}/CR-v1.1.pdf"),
        f"{NEWS}/rules-and-releases/riftbound-core-rules-patch-notes/",
        "cdn-verified",
    ),
    RulesDoc(
        "core",
        "1.2",
        "572377fcaa704a05f72eb42c104079d3b3bcf740",
        (f"{CDN}/572377fcaa704a05f72eb42c104079d3b3bcf740.pdf", f"{MIRROR}/CR-v1.2.pdf"),
        f"{NEWS}/rules-and-releases/riftbound-core-rules-spiritforged-patch-notes/",
        "cdn-verified",
    ),
    RulesDoc(
        "core",
        "1.3",
        "7affc578516386a973dffcc8132350856c5a104c",
        # Not on Riot's CDN under this hash (SPIKE_1, finding 1): mirror only.
        (f"{MIRROR}/CR-v1.3.pdf",),
        f"{NEWS}/rules-and-releases/riftbound-core-rules-unleashed-patch-notes/",
        "mirror-only-unverified",
    ),
    RulesDoc(
        "core",
        "1.4",
        "e9ac8e3d33e0f78cef296f5945aba7bc1313b086",
        (f"{CDN}/e9ac8e3d33e0f78cef296f5945aba7bc1313b086.pdf", f"{MIRROR}/CR-v1.4.pdf"),
        f"{NEWS}/announcements/core-rules-vendetta-patch-notes/",
        "cdn-verified",
    ),
)
