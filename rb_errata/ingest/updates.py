"""Slice 18: notice, register and size up a new Core Rules version.

Radiance was in force for 18 days before anything here noticed it. A new
version now takes this path, each step a make target:

1. `make check-updates`: the registry (data/sources.yaml) against the mirror's
   rules-manifest.json and, where reachable, Riot's Rules Hub. Exits 1 when
   the registry is behind, so a scheduled job can alert on it.
2. `make add-version V=1.5 NOTES=<patch notes url>`: downloads the PDF from
   the mirror at its current commit, pins its SHA-1, checks whether Riot's CDN
   serves the same bytes, and appends a validated registry entry.
3. `make fetch dates`, then `make version-impact V=1.5`: what the new version
   changes, which labelled questions cite rules it touches, and the
   meaning-flipping changes to draft version-change questions from.
4. `make ingest`, `make recall METHOD=as-of`, `make mcp-check`, as before.

Until step 4, search_rules warns that a newer version is not ingested
(tools.freshness). Nothing here writes labels: a version-change question
needs the check A44 added (the whole old version and the FAQs of its window),
which is a person's job.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any

import httpx
import yaml

from rb_errata.ingest import sources
from rb_errata.ingest.sources import CDN, MIRROR_RAW, MIRROR_REPO, RulesDoc, vkey

MANIFEST = f"{MIRROR_RAW}/main/sources/rules-manifest.json"
RULES_HUB = "https://playriftbound.com/en-us/rules-hub/"
IMPACT = Path("evals/impact")
_UA = {"User-Agent": "rb_errata (Riftbound rules research; non-commercial)"}
_CDN_PDF = re.compile(r"news_live/([0-9a-f]{40})\.pdf")
_NOTES = re.compile(r'href="([^"]*core-rules[^"]*patch-notes[^"]*)"')


# --- pure parts (unit-tested) --------------------------------------------------


def missing_versions(registered: list[str], manifest: dict[str, Any]) -> list[tuple[str, str]]:
    """Core Rules versions the mirror lists and the registry lacks: (version, set name)."""
    listed = manifest["coreRules"]["versions"]
    return sorted(
        ((v, str(meta.get("name", ""))) for v, meta in listed.items() if v not in registered),
        key=lambda x: vkey(x[0]),
    )


def hub_links(html: str, registered_sha1: set[str]) -> tuple[list[str], list[str]]:
    """From a Rules Hub page: CDN PDF hashes not registered, and patch-notes links."""
    pdfs = sorted(set(_CDN_PDF.findall(html)) - registered_sha1)
    notes = sorted({u if u.startswith("http") else "https://playriftbound.com" + u
                    for u in _NOTES.findall(html)})  # fmt: skip
    return pdfs, notes


def entry_block(
    version: str, name: str, sha1: str, urls: list[str], notes: str, provenance: str
) -> str:
    """The YAML text appended to the registry. Appended, not re-dumped, so the
    file's comments survive; the caller validates the whole file before writing."""
    lines = [
        "",
        f'- version: "{version}"',
        f"  name: {name}" if name else "  name: null",
        f"  sha1: {sha1}",
        "  urls:",
        *[f"    - {u}" for u in urls],
        f"  patch_notes: {notes}",
        f"  provenance: {provenance}",
    ]
    return "\n".join(lines) + "\n"


def check_new(version: str, notes: str, registry: tuple[RulesDoc, ...]) -> None:
    """Refuse a version that is not strictly newer, or notes that are not Riot's."""
    if not re.fullmatch(r"\d+\.\d+", version):
        raise SystemExit(f"V={version!r}: expected MAJOR.MINOR, like 1.5")
    newest = registry[-1].version
    if vkey(version) <= vkey(newest):
        raise SystemExit(f"V={version}: the registry already reaches v{newest}")
    if not notes.startswith("https://playriftbound.com/"):
        # The effective date is parsed from this page (A16); a fan site's
        # summary is not the announcement.
        raise SystemExit("NOTES must be Riot's patch notes page on playriftbound.com")


# --- network ---------------------------------------------------------------------


def _client() -> httpx.Client:
    return httpx.Client(headers=_UA, follow_redirects=True, timeout=120)


def check_updates() -> tuple[list[str], bool]:
    """Report lines, and whether the registry is up to date."""
    registry = sources.load(sources.REGISTRY)
    registered = [d.version for d in registry]
    lines = [f"registry: v{registered[0]} to v{registered[-1]} ({len(registered)} versions)"]
    behind = False
    with _client() as client:
        try:
            manifest = client.get(MANIFEST).raise_for_status().json()
        except httpx.HTTPError as exc:
            lines.append(f"mirror manifest unreachable: {exc}")
        else:
            for v, name in missing_versions(registered, manifest):
                behind = True
                lines.append(f"NEW  v{v} ({name or 'unnamed'}) is in the mirror, not the registry")
        try:
            html = client.get(RULES_HUB).raise_for_status().text
        except httpx.HTTPError as exc:
            lines.append(f"Riot Rules Hub unreachable from here ({type(exc).__name__}); skipped")
        else:
            pdfs, notes = hub_links(html, {d.sha1 for d in registry})
            for h in pdfs:
                behind = True
                lines.append(
                    f"NEW  Riot's Rules Hub links a PDF not in the registry: {CDN}/{h}.pdf"
                )
            known = {d.patch_notes for d in registry}
            for u in notes:
                if u not in known:
                    lines.append(f"     patch notes not in the registry: {u}")
    if behind:
        lines.append("Next: make add-version V=<version> NOTES=<Riot patch notes url>")
    else:
        lines.append("up to date")
    return lines, not behind


def _mirror_head() -> str:
    out = subprocess.run(
        ["git", "ls-remote", MIRROR_REPO, "HEAD"], capture_output=True, text=True, timeout=60
    )
    if out.returncode != 0 or not out.stdout:
        raise SystemExit(f"cannot read the mirror's commit: {out.stderr.strip()}")
    return out.stdout.split()[0]


def add_version(version: str, notes: str, registry_path: Path = sources.REGISTRY) -> list[str]:
    registry = sources.load(registry_path)
    check_new(version, notes, registry)
    commit = _mirror_head()
    mirror_url = f"{MIRROR_RAW}/{commit}/sources/CR-v{version}.pdf"
    with _client() as client:
        r = client.get(mirror_url)
        if r.status_code != 200:
            raise SystemExit(f"the mirror has no CR-v{version}.pdf at {commit[:12]}")
        sha1 = hashlib.sha1(r.content).hexdigest()
        cdn_url = f"{CDN}/{sha1}.pdf"
        try:
            cdn = client.get(cdn_url)
            cdn_ok = cdn.status_code == 200 and hashlib.sha1(cdn.content).hexdigest() == sha1
        except httpx.HTTPError:
            cdn_ok = False
        try:
            manifest = client.get(MANIFEST).raise_for_status().json()
            name = str(manifest["coreRules"]["versions"].get(version, {}).get("name", ""))
        except (httpx.HTTPError, KeyError):
            name = ""
    urls = [cdn_url, mirror_url] if cdn_ok else [mirror_url]
    provenance = "cdn-verified" if cdn_ok else "mirror-only-unverified"
    text = registry_path.read_text() + entry_block(version, name, sha1, urls, notes, provenance)
    sources.parse(yaml.safe_load(text))  # the whole registry must still load
    registry_path.write_text(text)
    return [
        f"registered v{version} ({name or 'unnamed'}): sha1 {sha1}, {provenance}",
        f"  mirror commit {commit[:12]}"
        + (
            "; Riot's CDN serves the same bytes"
            if cdn_ok
            else "; Riot's CDN not confirmed from here"
        ),
        "Next, in order:",
        "  make fetch dates            # download it, parse its effective date",
        f"  make version-impact V={version}  # what it changes, which labels it touches",
        "  make ingest                 # embed (cached text is not re-embedded)",
        "  make recall METHOD=as-of    # the question set on the new corpus",
        "  make mcp-check              # the server against that run",
    ]


# --- version-impact ----------------------------------------------------------------


def impact(version: str) -> list[str]:
    """What `version` changes against the version before it, as refs and counts."""
    from rb_errata import tools
    from rb_errata.ingest.align import align, flip_score, normalise
    from rb_errata.labels.review import load_questions

    registry = sources.load(sources.REGISTRY)
    versions = [d.version for d in registry]
    if version not in versions or versions.index(version) == 0:
        raise SystemExit(f"v{version} is not a registered version with a predecessor")
    prev = versions[versions.index(version) - 1]
    old, new = tools.rules(prev), tools.rules(version)
    matches, added = align(list(old.values()), list(new.values()))
    status: dict[str, tuple[str, str | None]] = {}
    for m in matches:
        if m.new is None:
            status[m.old.number] = ("removed", None)
        elif normalise(m.old.text) != normalise(m.new.text):
            status[m.old.number] = ("changed", m.new.number)
        else:
            kind = "unchanged" if m.old.number == m.new.number else "renumbered"
            status[m.old.number] = (kind, m.new.number)
    changed = [m for m in matches if m.new is not None and status[m.old.number][0] == "changed"]
    removed = [n for n, (k, _) in status.items() if k == "removed"]

    touched: dict[str, list[str]] = {}
    for q in load_questions():
        hits = []
        for ref in q["expect_sources"]:
            if ref.startswith(f"core@{prev}:"):
                kind, to = status.get(ref.split(":", 1)[1], ("missing", None))
                if kind in ("changed", "removed"):
                    hits.append(f"{ref} {kind}" + (f" -> core@{version}:{to}" if to else ""))
        if hits:
            touched.setdefault(q["stratum"], []).append(f"{q['id']}: {'; '.join(hits)}")

    by_stratum: dict[str, int] = {}
    for q in load_questions():
        if any(r.startswith(f"core@{prev}:") for r in q["expect_sources"]):
            by_stratum[q["stratum"]] = by_stratum.get(q["stratum"], 0) + 1
    flips = sorted(changed, key=lambda m: -flip_score(m.old.text, m.new.text))  # type: ignore[union-attr]
    lines = [
        f"# Impact of core@{version} against core@{prev}",
        "",
        "Generated by `make version-impact`. Refs and counts only; rule text stays local.",
        "",
        f"Rules: {len(changed)} changed, {len(added)} added, {len(removed)} removed "
        f"(matched by wording, never by number; A15).",
        "",
        f"## Labelled questions citing a v{prev} rule that changed or was removed",
        "",
        "Their labels are dated before this version, so they stay right; a question "
        "dated after it would have to be rechecked.",
        "",
        f"| stratum | questions citing v{prev} | touched |",
        "|---|---|---|",
        *[f"| {s} | {n} | {len(touched.get(s, []))} |" for s, n in by_stratum.items()],
        "",
        *[f"- {line}" for s in by_stratum for line in touched.get(s, [])],
        "",
        "## Changes to draft version-change questions from",
        "",
        "Meaning-flipping wording first (may/must, not). A draft becomes a label only",
        "after the A44 check: the whole old version, and the FAQs published in its window.",
        "",
        "| old | new | flip score |",
        "|---|---|---|",
        *[f"| core@{prev}:{m.old.number} | core@{version}:{m.new.number} | "  # type: ignore[union-attr]
          f"{flip_score(m.old.text, m.new.text)} |" for m in flips[:25]],  # type: ignore[union-attr]
    ]  # fmt: skip
    return lines


def write_impact(version: str) -> Path:
    IMPACT.mkdir(parents=True, exist_ok=True)
    out = IMPACT / f"core-{version}.md"
    out.write_text("\n".join(impact(version)) + "\n")
    return out


# --- one command for the whole path ------------------------------------------------


def integrate(
    version: str, notes: str, effective_file: Path = Path("data/effective_dates.json")
) -> int:
    """Every step of the new-version path, each as its own process.

    Separate processes because `add-version` changes the registry that every
    module loads at import; an in-process chain would ingest with the old one.
    Stops at the first failing step, and before the database is rebuilt if the
    new version's effective date was not parsed: A16 would refuse it anyway,
    and a corpus rebuilt without it would only look up to date.
    """
    import sys

    def step(*args: str) -> int:
        print(f"\n=== make {' '.join(args)}", flush=True)
        return subprocess.run([sys.executable, "-m", "rb_errata.cli", *args]).returncode

    registered = [d.version for d in sources.load(sources.REGISTRY)]
    if version not in registered and step("add-version", version, "--notes", notes):
        return 1
    for name in ("fetch", "dates"):
        if step(name):
            return 1
    dated = {r["version"]: r for r in json.loads(effective_file.read_text())}
    if dated.get(version, {}).get("status") != "known":
        reason = dated.get(version, {}).get("reason", "no row")
        print(f"\nSTOP: v{version}'s effective date was not parsed ({reason}).\n"
              "Run `make dates-debug` and paste its output; nothing was re-ingested.")  # fmt: skip
        return 1
    print(f"\nv{version} effective {dated[version]['effective']} ({dated[version]['basis']})")
    later: list[tuple[str, ...]] = [
        ("version-impact", version),
        ("ingest",),
        ("recall", "--method", "as-of"),
        ("mcp-check",),
    ]
    for args in later:
        if step(*args):
            return 1
    print(f"\nv{version} integrated. Commit data/, evals/ and push.")
    return 0
