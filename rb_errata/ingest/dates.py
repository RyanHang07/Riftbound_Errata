"""Effective dates from patch notes, and the validity intervals built on them.

A16 chose automatic parsing over a hand-made table, accepting that a parsing
mistake would put a wrong `valid_from` on every chunk of a version. So the
parser is built to say "unknown" rather than be wrong:

- It looks only for a date attached to an effective-date phrase.
- Exactly one distinct date on the page: known. None, or several: unknown.
- It never falls back to the printed "Last Updated" date, which SPIKE_1
  showed precedes the effective date by days.

Pages were never visible from the session that wrote this (Riot's site is
blocked there), so the phrase patterns come from search-result snippets such
as "have an effective date of December 12, 2025" and "became effective on
July 24, 2026". Expect the first real run to need adjustments; the output
shows every candidate found, so a wrong guess is visible rather than silent.
"""

from __future__ import annotations

import html
import re
from collections.abc import Mapping
from dataclasses import asdict, dataclass, field
from datetime import date
from typing import Any

from rb_errata.ingest.pdf import parse_date

_MONTHS = "January|February|March|April|May|June|July|August|September|October|November|December"
_DATE = (
    rf"(?:(?:{_MONTHS})\s+\d{{1,2}},?\s+20\d\d"  # July 24, 2026
    rf"|\d{{1,2}}\s+(?:{_MONTHS})\s+20\d\d"  # 24 July 2026
    r"|20\d\d-\d\d-\d\d"  # 2026-07-24
    r"|\d{1,2}/\d{1,2}/20\d\d)"  # 7/24/2026
)
# An effective-date phrase, then at most 60 characters with no sentence end,
# then a date. Bounded so a date in the next sentence is never attached.
_EFFECTIVE = re.compile(
    r"(?:effective|in effect|take[sn]? effect|go(?:es)? into effect)"
    rf"[^.!?]{{0,60}}?(?P<date>{_DATE})",
    re.IGNORECASE,
)


def _to_date(raw: str) -> date:
    raw = " ".join(raw.replace(",", " ").split())
    m = re.fullmatch(rf"({_MONTHS}) (\d{{1,2}}) (20\d\d)", raw, re.IGNORECASE)
    if m:
        month = _MONTHS.lower().split("|").index(m.group(1).lower()) + 1
        return date(int(m.group(3)), month, int(m.group(2)))
    m = re.fullmatch(rf"(\d{{1,2}}) ({_MONTHS}) (20\d\d)", raw, re.IGNORECASE)
    if m:
        month = _MONTHS.lower().split("|").index(m.group(2).lower()) + 1
        return date(int(m.group(3)), month, int(m.group(1)))
    return parse_date(raw)


def page_text(raw_html: str) -> str:
    """Visible text plus script contents, tags removed.

    Script contents are kept on purpose: if the site renders client-side, the
    article text exists only inside a JSON blob in a <script> tag.
    """
    no_tags = re.sub(r"<[^>]+>", " ", raw_html)
    # JSON blobs escape quotes and newlines; unescape both layers.
    unescaped = html.unescape(no_tags).replace("\\n", " ").replace('\\"', '"')
    return " ".join(unescaped.split())


@dataclass
class EffectiveDate:
    version: str
    url: str | None
    status: str  # "known" | "unknown"
    effective: str | None = None  # ISO date when known
    reason: str = ""
    # Every candidate seen: ISO date and character offset in the page text.
    # Offsets, not quotes: the audit file must not contain Riot's text.
    candidates: list[dict[str, Any]] = field(default_factory=list)
    page_sha1: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def find_effective_date(version: str, url: str | None, raw_html: str | None) -> EffectiveDate:
    if url is None:
        return EffectiveDate(
            version, None, "unknown", reason="no announcement exists for this version"
        )
    if raw_html is None:
        return EffectiveDate(version, url, "unknown", reason="page not fetched")
    text = page_text(raw_html)
    candidates: list[dict[str, Any]] = []
    for m in _EFFECTIVE.finditer(text):
        try:
            candidates.append({"date": _to_date(m.group("date")).isoformat(), "offset": m.start()})
        except ValueError:
            continue  # an impossible date like 2/30 is not a candidate
    distinct: list[str] = sorted({str(c["date"]) for c in candidates})
    if len(distinct) == 1:
        return EffectiveDate(version, url, "known", distinct[0], "one distinct date", candidates)
    reason = "no effective-date phrase found" if not distinct else f"ambiguous: {distinct}"
    return EffectiveDate(version, url, "unknown", None, reason, candidates)


@dataclass(frozen=True)
class Interval:
    valid_from: date
    valid_to: date | None  # None means "still current", never a sentinel date


def intervals(
    ordered_versions: list[str], effective: Mapping[str, date | None], printed: Mapping[str, date]
) -> tuple[dict[str, Interval], dict[str, str]]:
    """Validity window per version, plus the reason each refused version was refused.

    A version ends when the next one takes effect. So a version is datable
    only if its own effective date AND its successor's are known: otherwise
    its end is unknown, and bridging the gap would claim it was the rule
    during a period nobody established.
    """
    ok: dict[str, Interval] = {}
    refused: dict[str, str] = {}
    for i, v in enumerate(ordered_versions):
        start = effective.get(v)
        if start is None:
            refused[v] = "effective date unknown"
            continue
        if start < printed[v]:
            refused[v] = f"effective {start} is before its printed date {printed[v]}"
            continue
        if i + 1 < len(ordered_versions):
            nxt = effective.get(ordered_versions[i + 1])
            if nxt is None:
                refused[v] = f"successor {ordered_versions[i + 1]}'s effective date is unknown"
                continue
            if nxt <= start:
                refused[v] = f"successor takes effect {nxt}, not after this version's {start}"
                continue
            ok[v] = Interval(start, nxt)
        else:
            ok[v] = Interval(start, None)
    return ok, refused
