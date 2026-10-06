"""The site's numbers come from the committed runs, never from a hand edit."""

from __future__ import annotations

from rb_errata import site_data


def test_export_reproduces_the_recorded_comparisons() -> None:
    data = site_data.build()
    runs = {r["run"]: r for r in data["runs"]}
    qwen = runs["recall-as-of-qwen3-2026-10-04T1415Z"]["groups"]["version-change"]
    # A29: 44 of 56 at recall@5, 12 gained and 1 lost against nomic.
    assert (qwen["at5"]["k"], qwen["at5"]["n"]) == (44, 56)
    assert (qwen["vs_paired"]["gained"], qwen["vs_paired"]["lost"]) == (12, 1)
    # A24 / A27: outdated copy above the hit, 16 of 56 naive, 0 with the date filter.
    assert (
        runs["recall-2026-10-02T2236Z"]["groups"]["version-change"]["outdated_above_hit5"]["k"]
        == 16
    )
    assert (
        runs["recall-as-of-2026-10-02T2251Z"]["groups"]["version-change"]["outdated_above_hit5"][
            "k"
        ]
        == 0
    )


def test_cards_are_only_this_projects_own_questions() -> None:
    # The CC BY-SA rulings stay out of the site's carousel; only the
    # version-change questions written for this project are exported.
    from rb_errata.labels.review import load_questions

    written = {q["id"] for q in load_questions() if q["stratum"] == "version-change"}
    assert {c["id"] for c in site_data.build()["cards"]} <= written


def test_committed_export_is_current() -> None:
    # A stale site/data/results.json would publish numbers the runs no longer
    # give. Regenerate with `make site-data`.
    import json

    assert json.loads(site_data.OUT.read_text()) == json.loads(json.dumps(site_data.build()))
