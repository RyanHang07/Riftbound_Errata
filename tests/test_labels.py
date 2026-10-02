"""Contract tests for the labelled set: parser, builder checks, power maths."""

from pathlib import Path

import pytest

from rb_errata.labels import power
from rb_errata.labels.build import validate
from rb_errata.labels.rulings import parse_file

MDX = """---
title: "Test Card"
createdAt: "2026-04-19"
reviewedCoreRulesVersion: "1.4"
authors:
- name: "A. Author"
---

## Does <Card name="Test Card" /> trigger if countered? [#countered]

No.
It needs the spell to <Term item="resolution">resolve</Term>.<Rule number="419.4.a" />
Paying <Energy value={2} /> does not help.<Rule number="419.4.a.1" /><Rule number="419.4.a" />

## Does Deflect apply? [#deflect]

Per the [FAQ](https://playriftbound.com/en-us/news/x-faq), <Deflect /> applies.
<Rule number="809.1.c" />
"""


def parse(tmp_path: Path, text: str = MDX) -> list:  # type: ignore[type-arg]
    f = tmp_path / "content" / "cards" / "test-card.mdx"
    f.parent.mkdir(parents=True)
    f.write_text(text)
    return parse_file(f, tmp_path)


def test_questions_answers_and_citations(tmp_path: Path) -> None:
    a, _ = parse(tmp_path)
    assert a.id == "r-test-card-countered" and a.question == "Does Test Card trigger if countered?"
    assert a.answer_short == "no"
    assert a.rule_numbers == ["419.4.a", "419.4.a.1"]  # de-duplicated, in order
    assert "[2]" in a.answer and "resolve" in a.answer and "<" not in a.answer
    assert not a.faq_backed


def test_faq_backed_answers_are_flagged_per_question(tmp_path: Path) -> None:
    _, b = parse(tmp_path)
    assert b.faq_backed and "Deflect applies" in b.answer


def test_unknown_component_is_an_error_not_a_silent_loss(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="unknown MDX component"):
        parse(tmp_path, MDX.replace("No.", '<Mystery kind="x">No.</Mystery>'))


def test_heading_without_anchor_is_an_error(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="without an anchor"):
        parse(tmp_path, MDX.replace(" [#deflect]", ""))


def test_validate_reports_refs_missing_from_the_corpus() -> None:
    entries = [{"id": "q", "expect_sources": ["core@1.4:419.4.a", "core@1.4:999.9"]}]
    problems = validate(entries, {"core@1.4:419.4.a"})
    assert problems == ["q: cites refs not in the corpus: ['core@1.4:999.9']"]


def test_wilson_and_mcnemar_match_known_values() -> None:
    lo, hi = power.wilson(18, 20)
    assert (round(lo, 2), round(hi, 2)) == (0.70, 0.97)
    assert power.min_discordant_all_one_way() == 6
    assert power.mcnemar_power(20, 0.0, 0.9) == 0.0


def test_committed_question_set_references_only_ingested_rules() -> None:
    import yaml

    from rb_errata.labels.build import corpus_refs

    entries = yaml.safe_load(Path("evals/questions.yaml").read_text())
    assert validate(entries, corpus_refs()) == []
    assert {e["stratum"] for e in entries} == {
        "expert-ruling",
        "expert-ruling-faq",
        "version-change",
    }
    assert all(e["version_dependent"] in (True, None) for e in entries)


def test_review_trim_keeps_later_strata(monkeypatch: pytest.MonkeyPatch) -> None:
    # Trimming rulings must not change which FAQ and version-change questions
    # are drawn, or answers already given would point at a different sample.
    from rb_errata.labels import review

    entries = [
        {"id": f"{s}-{i:03}", "stratum": s}
        for s, n in [("expert-ruling", 160), ("expert-ruling-faq", 8), ("version-change", 56)]
        for i in range(n)
    ]
    trimmed = review.sample(entries)
    monkeypatch.setattr(review, "KEEP", {})
    full = review.sample(entries)
    assert len(trimmed) == 40
    assert trimmed == full[:20] + full[40:]


def test_review_file_matches_sample() -> None:
    # The committed verdicts must cover exactly the seeded sample, so nobody
    # can add or drop a reviewed question by hand.
    import yaml

    from rb_errata.labels import review

    rows = yaml.safe_load(review.REVIEW.read_text())
    assert [r["id"] for r in rows] == [e["id"] for e in review.sample(review.load_questions())]
