"""Download the source documents into data/raw/ (gitignored: Riot's text never
enters the repository). PDFs must match their pinned SHA-1 or they are refused.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import httpx

from rb_errata.ingest.sources import CORE_RULES, RulesDoc

RAW = Path("data/raw")
FETCH_LOG = RAW / "fetched.json"
_UA = {"User-Agent": "rb_errata (Riftbound rules research; non-commercial)"}


def sha1_of(path: Path) -> str:
    h = hashlib.sha1()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def fetch_pdf(doc: RulesDoc, client: httpx.Client, raw: Path = RAW) -> tuple[str, str]:
    """Returns (status line, URL that served the verified bytes, or "")."""
    dest = raw / doc.filename
    if dest.exists() and sha1_of(dest) == doc.sha1:
        return f"cached    {doc.id}", ""
    errors = []
    for url in doc.urls:
        tmp = dest.with_suffix(".part")
        try:
            with client.stream("GET", url) as r:
                r.raise_for_status()
                with tmp.open("wb") as f:
                    for block in r.iter_bytes():
                        f.write(block)
        except httpx.HTTPError as exc:
            errors.append(f"{url}: {exc}")
            continue
        got = sha1_of(tmp)
        if got != doc.sha1:
            # Wrong bytes are worse than no bytes: refuse, and keep looking.
            tmp.unlink()
            errors.append(f"{url}: SHA-1 {got[:12]} != pinned {doc.sha1[:12]}")
            continue
        tmp.replace(dest)
        return f"obtained  {doc.id} from {url}", url
    return f"FAILED    {doc.id}: " + "; ".join(errors), ""


def fetch_page(url: str, dest: Path, client: httpx.Client) -> str:
    try:
        r = client.get(url)
        r.raise_for_status()
    except httpx.HTTPError as exc:
        return f"FAILED    {dest.name}: {exc}"
    dest.write_text(r.text)
    return f"obtained  {dest.name}"


def patch_notes_path(doc: RulesDoc, raw: Path = RAW) -> Path:
    return raw / f"patch-notes-{doc.doc}-{doc.version}.html"


def fetch_all(raw: Path = RAW) -> tuple[list[str], bool]:
    raw.mkdir(parents=True, exist_ok=True)
    log: dict[str, str] = json.loads(FETCH_LOG.read_text()) if FETCH_LOG.exists() else {}
    lines, ok = [], True
    with httpx.Client(headers=_UA, follow_redirects=True, timeout=120) as client:
        for doc in CORE_RULES:
            line, url = fetch_pdf(doc, client, raw)
            lines.append(line)
            ok &= not line.startswith("FAILED")
            if url:
                log[doc.id] = url
            if doc.patch_notes:
                lines.append(fetch_page(doc.patch_notes, patch_notes_path(doc, raw), client))
    FETCH_LOG.write_text(json.dumps(log, indent=2))
    return lines, ok
