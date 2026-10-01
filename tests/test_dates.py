"""Contract tests for dates: printed, effective, and the intervals built on them."""

import json
from datetime import date
from pathlib import Path

import pytest

from rb_errata.ingest.dates import debug_page, find_effective_date, intervals
from rb_errata.ingest.pdf import parse_date, printed_date

URL = "https://example.test/patch-notes"


def test_printed_date_accepts_both_formats_riot_uses() -> None:
    assert printed_date("Rules\nLast Updated: 2026-03-30\n000.") == date(2026, 3, 30)
    assert printed_date("Rules Last Updated 7/16/2026 000.") == date(2026, 7, 16)


def test_unknown_date_format_is_refused_not_guessed() -> None:
    with pytest.raises(ValueError):
        parse_date("16.07.2026")
    with pytest.raises(ValueError):
        printed_date("Rules without a date")


def test_one_effective_date_is_known() -> None:
    page = "<p>These rules updates have an effective date of December 12, 2025.</p>"
    r = find_effective_date("1.2", URL, page)
    assert (r.status, r.effective) == ("known", "2025-12-12")


def test_repeated_mentions_of_the_same_date_are_still_one_date() -> None:
    page = "Effective July 24, 2026. ... the update became effective on July 24, 2026."
    assert find_effective_date("1.4", URL, page).effective == "2026-07-24"


def test_date_found_inside_a_script_json_blob() -> None:
    # A client-rendered site may hold the article only in a <script> tag.
    page = '<script>{"body":"Changes take effect on 24 July 2026.\\n"}</script>'
    assert find_effective_date("1.4", URL, page).effective == "2026-07-24"


def test_two_different_dates_is_unknown_not_a_pick() -> None:
    page = "Rules are effective March 30, 2026. Errata goes into effect April 8, 2026."
    r = find_effective_date("1.3", URL, page)
    assert r.status == "unknown" and "ambiguous" in r.reason
    assert len(r.candidates) == 2


HEAD = '<script type="application/ld+json">{"datePublished":"2026-03-30T16:00:00.000Z"}</script>'


def test_no_stated_date_uses_the_announcement_date_and_says_so() -> None:
    # A17. A body date with no effective phrase is still ignored: the result
    # comes from the page's publish metadata, and is labelled as inferred.
    r = find_effective_date("1.3", URL, HEAD + "<p>Released in China on April 8, 2026.</p>")
    assert (r.status, r.effective, r.basis) == ("known", "2026-03-30", "announcement-date")


def test_no_stated_date_and_no_publish_date_is_unknown() -> None:
    r = find_effective_date("1.3", URL, "Published March 30, 2026. New rules for Unleashed.")
    assert r.status == "unknown" and r.reason == "no stated date and no publish date"


def test_publish_dates_of_related_articles_are_not_used() -> None:
    page = "<p>Rules notes.</p>" + "x" * 7000 + '{"datePublished":"2026-08-14T01:00:00.000Z"}'
    assert find_effective_date("1.3", URL, page).status == "unknown"


def test_a_stated_date_beats_the_announcement_date() -> None:
    r = find_effective_date("1.2", URL, HEAD + "<p>An effective date of December 12, 2025.</p>")
    assert (r.effective, r.basis) == ("2025-12-12", "stated")


def test_date_in_the_next_sentence_is_not_attached() -> None:
    r = find_effective_date("1.3", URL, "Effective immediately. The set launches May 8, 2026.")
    assert r.status == "unknown"


def test_no_announcement_is_unknown() -> None:
    assert find_effective_date("1.0", None, None).status == "unknown"


V = ["1.0", "1.1", "1.2"]
PRINTED = {"1.0": date(2025, 6, 2), "1.1": date(2025, 10, 1), "1.2": date(2025, 12, 1)}


def test_intervals_chain_and_the_last_is_open() -> None:
    eff = {"1.0": date(2025, 6, 2), "1.1": date(2025, 10, 24), "1.2": date(2025, 12, 12)}
    ok, refused = intervals(V, eff, PRINTED)
    assert ok["1.0"].valid_to == date(2025, 10, 24)
    assert ok["1.2"].valid_to is None and not refused


def test_unknown_start_refuses_that_version_only() -> None:
    eff = {"1.0": None, "1.1": date(2025, 10, 24), "1.2": date(2025, 12, 12)}
    ok, refused = intervals(V, eff, PRINTED)
    assert set(ok) == {"1.1", "1.2"} and set(refused) == {"1.0"}


def test_unknown_successor_refuses_the_predecessor_rather_than_bridging() -> None:
    eff = {"1.0": date(2025, 6, 2), "1.1": None, "1.2": date(2025, 12, 12)}
    ok, refused = intervals(V, eff, PRINTED)
    # 1.0 would otherwise claim to be the rule until December: a gap nobody established.
    assert "1.0" in refused and "successor" in refused["1.0"]
    assert set(ok) == {"1.2"}


def test_effective_before_printed_is_refused_as_suspicious() -> None:
    eff = {"1.0": date(2025, 6, 2), "1.1": date(2025, 9, 1), "1.2": date(2025, 12, 12)}
    _, refused = intervals(V, eff, PRINTED)
    assert "1.1" in refused


# A16: the two effective dates already established from search results are
# known answers. Once `make dates` has produced the committed audit file, the
# parser's output must agree with both, or the parser is wrong.
KNOWN = {"1.2": "2025-12-12", "1.4": "2026-07-24"}
AUDIT = Path("data/effective_dates.json")


@pytest.mark.skipif(not AUDIT.exists(), reason="data/effective_dates.json not generated yet")
def test_parsed_effective_dates_match_the_known_answers() -> None:
    rows = {r["version"]: r for r in json.loads(AUDIT.read_text())}
    for version, expected in KNOWN.items():
        assert rows[version]["status"] == "known", rows[version]["reason"]
        assert rows[version]["effective"] == expected
        # Both known answers were stated on their pages; inferring either
        # would mean the parser missed the sentence it exists to find.
        assert rows[version]["basis"] == "stated"


def test_debug_shows_yearless_dates_the_parser_ignores() -> None:
    out = "\n".join(debug_page("<p>The new rules go live Friday, May 8th for everyone.</p>"))
    assert "dates without a year: 1 found" in out and "full dates: 0 found" in out


def test_dates_in_related_articles_are_not_this_articles_date() -> None:
    page = (
        "<article>The rules update will be effective on July 24, 2026.</article>"
        "<aside>Related Articles <a>Ban List Updates (Effective September 18, 2026)</a></aside>"
    )
    r = find_effective_date("1.4", URL, page)
    assert (r.status, r.effective) == ("known", "2026-07-24")
