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


# Every patch-notes page lists other news under this heading. Found on the
# first real run: the v1.4 page linked "September Ban List Updates (Effective
# September 18, 2026)" there, which made v1.4 look ambiguous. The article body,
# and only the article body, comes before the first occurrence.
_RELATED = "Related Articles"


def article_text(text: str) -> str:
    """The page text up to the related-articles list (the whole text if absent;
    the ambiguity guard still applies then)."""
    cut = text.find(_RELATED)
    return text if cut == -1 else text[:cut]


# The page head carries schema.org metadata: "datePublished":"2025-10-24T01:00:00.000Z".
# Only the head is searched; related-article entries further down carry
# their own publish dates.
_PUBLISHED = re.compile(r'"datePublished"\s*:\s*"(20\d\d-\d\d-\d\d)T')
_HEAD_CHARS = 6000


def announcement_date(raw_html: str) -> date | None:
    """The page's own publish date, if its head states exactly one.

    The timestamp is UTC. A late-evening US Pacific post lands on the next UTC
    day (v1.1's 01:00Z is Oct 23 in California), so these dates can be one day
    late for a reader in the Americas. Recorded, not corrected: the effect is
    confined to questions dated on that single day.
    """
    found = {m.group(1) for m in _PUBLISHED.finditer(raw_html[:_HEAD_CHARS])}
    if len(found) != 1:
        return None
    return date.fromisoformat(found.pop())


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
    # "stated": the page says when the rules take effect.
    # "announcement-date": it says nothing, so the page's publish date is used
    # (A17). Kept separate so the audit file shows which dates are inferred.
    basis: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def find_effective_date(version: str, url: str | None, raw_html: str | None) -> EffectiveDate:
    if url is None:
        return EffectiveDate(
            version, None, "unknown", reason="no announcement exists for this version"
        )
    if raw_html is None:
        return EffectiveDate(version, url, "unknown", reason="page not fetched")
    text = article_text(page_text(raw_html))
    candidates: list[dict[str, Any]] = []
    for m in _EFFECTIVE.finditer(text):
        try:
            candidates.append({"date": _to_date(m.group("date")).isoformat(), "offset": m.start()})
        except ValueError:
            continue  # an impossible date like 2/30 is not a candidate
    distinct: list[str] = sorted({str(c["date"]) for c in candidates})
    if len(distinct) == 1:
        return EffectiveDate(
            version, url, "known", distinct[0], "one distinct date", candidates, basis="stated"
        )
    if distinct:
        return EffectiveDate(version, url, "unknown", None, f"ambiguous: {distinct}", candidates)
    # A17: no stated date means the rules took effect when announced. Riot's
    # own wording supports this default: the Spiritforged notes say "Rather
    # than taking effect immediately, these rules will have an effective
    # date of...", treating immediate effect as the norm and a delay as the
    # thing worth stating. The announcement's machine-readable publish date
    # is used, NOT the PDF's printed date, which can be weeks earlier.
    published = announcement_date(raw_html)
    if published is None:
        return EffectiveDate(version, url, "unknown", None, "no stated date and no publish date")
    return EffectiveDate(
        version, url, "known", published.isoformat(),
        "no stated date; announcement publish date used", candidates, basis="announcement-date",
    )  # fmt: skip


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


_PHRASE = re.compile(
    r"effective|in effect|take[sn]? effect|go(?:es)? into effect|as of|starting|go(?:es)? live",
    re.IGNORECASE,
)
# Dates with no year ("Friday, May 8th"): the effective-date pattern ignores
# them, so if a page only uses this form the diagnostic must show it.
_YEARLESS = re.compile(
    rf"(?:{_MONTHS})\s+\d{{1,2}}(?:st|nd|rd|th)?(?!\d|,?\s+20\d\d)", re.IGNORECASE
)


def debug_page(raw_html: str, limit: int = 8) -> list[str]:
    """Where a page mentions dates and effective-ness, with a little context.

    For tuning the parser against pages the authoring session could not see.
    Prints short excerpts of Riot's text to the local terminal only; nothing
    here is written to disk or committed.
    """
    text = page_text(raw_html)
    out = [
        f"  page text: {len(text):,} chars; client-rendered JSON present: "
        f"{'__NEXT_DATA__' in raw_html}"
    ]

    def show(label: str, pattern: re.Pattern[str], before: int, after: int) -> None:
        hits = list(pattern.finditer(text))
        out.append(
            f"  {label}: {len(hits)} found"
            + (f", first {limit} shown" if len(hits) > limit else "")
        )
        for m in hits[:limit]:
            a, b = max(0, m.start() - before), min(len(text), m.end() + after)
            out.append(f"    @{m.start():>6}: ...{text[a:b]}...")

    show("effective-type phrases", _PHRASE, 30, 90)
    show("full dates", re.compile(_DATE, re.IGNORECASE), 70, 10)
    show("dates without a year", _YEARLESS, 70, 10)
    return out
