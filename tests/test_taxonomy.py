"""Slice 12 contracts: one category per miss, decided by a fixed rule."""

from __future__ import annotations

from typing import Any

import pytest

from rb_errata import taxonomy


def g(rank: int | None, state: str = "graded") -> dict[str, Any]:
    return {"state": state, "hit_rank": rank}


@pytest.mark.parametrize("rank", [1, 5])
def test_hit_has_no_category(rank: int) -> None:
    assert taxonomy.classify({"category": "cards"}, g(rank)) is None


@pytest.mark.parametrize(
    ("category", "rank", "want"),
    [
        # In the top 20, below the cutoff: below-cutoff whatever the source says.
        ("cards", 6, "below-cutoff"),
        ("mechanics", 20, "below-cutoff"),
        (None, 11, "below-cutoff"),
        # Outside the top 20: the source category decides.
        ("cards", None, "card-not-in-corpus"),
        ("general-rules", None, "rule-only"),
        ("mechanics", None, "rule-only"),
        # No source category (version-change) or an unknown one is never
        # guessed into a bucket.
        (None, None, "unclassified"),
        ("something-new", None, "unclassified"),
    ],
)
def test_miss_categories(category: str | None, rank: int | None, want: str) -> None:
    q = {} if category is None else {"category": category}
    assert taxonomy.classify(q, g(rank)) == want


def test_failed_search_is_unclassified() -> None:
    # An errored row is a miss of unknown cause, not a retrieval failure.
    assert taxonomy.classify({"category": "cards"}, g(None, state="unknown")) == "unclassified"


def test_every_category_listed_even_at_zero(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(taxonomy, "load_questions", lambda: [{"stratum": "a"}, {"stratum": "b"}])
    out = taxonomy.counts({"q": {"stratum": "a", "category": "rule-only"}})
    assert out == {
        "a": {"below-cutoff": 0, "card-not-in-corpus": 0, "rule-only": 1, "unclassified": 0},
        "b": dict.fromkeys(taxonomy.CATEGORIES, 0),
    }
