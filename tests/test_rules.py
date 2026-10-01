"""Contract tests for rule parsing and chunking. Synthetic text, not Riot's."""

import pytest

from rb_errata.ingest.chunk import HARD_LIMIT, chunk_rules
from rb_errata.ingest.rules import parse_rules, sort_key

DOC = """Example Rules
Last Updated: 2026-01-02
100. Setup
101. Decks
101.1. A deck has forty cards.
101.2. Each card may appear up to three times.
101.2.a. Tokens do not count.
101.2.a.1. Nor do markers.
See rule
300. for the battle step.
102. Hands
102.1. Each player draws four.
300. Battle
300.1. The attacker declares first.
"""


def test_parses_numbers_text_and_wrapped_lines() -> None:
    rules = {r.number: r.text for r in parse_rules(DOC)}
    assert list(rules)[:3] == ["100", "101", "101.1"]
    assert rules["101.2.a.1"].startswith("Nor do markers.")


def test_a_wrapped_cross_reference_is_folded_back_not_taken_as_a_rule() -> None:
    # "300." starts a line inside 101.2.a.1. A greedy parser would accept it
    # and then reject 102 and 102.1 as out of order. The longest increasing
    # subsequence keeps 102 and 102.1, and the stray line stays as text.
    rules = {r.number: r.text for r in parse_rules(DOC)}
    assert "102" in rules and "102.1" in rules
    assert "300. for the battle step." in rules["101.2.a.1"]
    assert rules["300"] == "Battle"


def test_letters_and_numbers_order_correctly() -> None:
    assert sort_key("101.2.a.1") < sort_key("101.2.b") < sort_key("101.10")


def words(s: str) -> int:
    return len(s.split())


def test_every_rule_lands_in_some_chunk() -> None:
    rules = parse_rules(DOC)
    chunks = chunk_rules(rules, words)
    assert {r.number for r in rules} <= {ref for c in chunks for ref in c.refs}


def test_heading_is_prefixed_and_listed_in_refs() -> None:
    chunks = chunk_rules(parse_rules(DOC), words)
    c = next(c for c in chunks if c.source_ref == "101.2")
    assert c.text.startswith("101. Decks")
    assert c.refs[0] == "101" and "101.2.a.1" in c.refs


def test_over_cap_group_splits_at_rule_boundaries() -> None:
    long = "\n".join(f"200.1.{chr(97 + i)}. " + "word " * 150 for i in range(4))
    chunks = chunk_rules(parse_rules("200. Big\n200.1. Group\n" + long), words)
    group = [c for c in chunks if c.source_ref == "200.1"]
    assert len(group) > 1
    assert [r for c in group for r in c.refs if r != "200"] == [
        "200.1", "200.1.a", "200.1.b", "200.1.c", "200.1.d",
    ]  # fmt: skip


def test_a_rule_too_long_to_embed_is_an_error_not_a_silent_truncation() -> None:
    with pytest.raises(ValueError, match="exceeds"):
        chunk_rules(parse_rules("200. Big\n200.1. " + "word " * (HARD_LIMIT + 10)), words)
