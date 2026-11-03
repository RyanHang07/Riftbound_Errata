"""Slice 11 contracts: quotes removed, verdicts parsed strictly, kappa right, sample blind."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from rb_errata import answers, judge
from rb_errata.generate.quotes import redact
from rb_errata.labels.agreement import bootstrap, kappa, landis_koch

RULE = "A card that is Countered is not considered to have been played for abilities that trigger."


# --- quote guard -------------------------------------------------------------------


def test_copied_run_is_removed_and_named() -> None:
    text, n = redact(f"No. {RULE.upper()} So it does not trigger.", [("core@1.4:426.1.b", RULE)])
    assert n == 1
    # The run ends at the last copied word; the sentence's full stop stays.
    assert text == "No. [quoted text from core@1.4:426.1.b removed]. So it does not trigger."


def test_short_overlap_and_paraphrase_survive() -> None:
    answer = "A countered card is not considered played, so nothing triggers [core@1.4:426.1.b]."
    assert redact(answer, [("core@1.4:426.1.b", RULE)]) == (answer, 0)


def test_two_quotes_from_two_passages() -> None:
    other = "Units enter the board exhausted unless an effect says they enter ready instead."
    answer = f"First: {RULE} Second: {other}"
    text, n = redact(answer, [("a", RULE), ("b", other)])
    assert (
        n == 2 and "[quoted text from a removed]" in text and "[quoted text from b removed]" in text
    )


# --- judge -----------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("raw", "want"),
    [
        ('{"verdict": "correct", "reason": "same"}', ("correct", "same")),
        ('{"verdict": "Not answered", "reason": "x"}', ("not_answered", "x")),
        ('noise {"verdict": "incorrect"} noise', ("incorrect", "")),
        ('{"verdict": "mostly right"}', ("unparsed", '{"verdict": "mostly right"}')),
        ("I think it is correct.", ("unparsed", "I think it is correct.")),
    ],
)
def test_verdicts_parse_strictly(raw: str, want: tuple[str, str]) -> None:
    # "unparsed" is never guessed into a verdict.
    assert judge.parse(raw) == want


def test_reference_for_rulings_and_version_change() -> None:
    assert judge.reference({"id": "r-x", "answer": "No, because."}) == "No, because."
    vc = {"id": "v-x-v1.2", "change": "Old: no. Current: yes.", "as_of": "2026-02-04"}
    assert "the OLD answer" in judge.reference(vc)
    assert "the CURRENT answer" in judge.reference({**vc, "id": "v-x-current"})


def test_judge_never_sees_passages() -> None:
    # The template has no slot for retrieved text: the judge cannot be
    # persuaded by the same passage that misled the generator.
    assert "passage" not in judge.TEMPLATE.lower()


# --- agreement -------------------------------------------------------------------------


def test_kappa_worked_example() -> None:
    # 10 items, agree on 8. Rater a: 6 yes, 4 no; rater b: 6 yes, 4 no.
    a = ["y"] * 6 + ["n"] * 4
    b = ["y"] * 5 + ["n"] + ["n"] * 3 + ["y"]
    # observed 0.8; expected (6*6 + 4*4) / 100 = 0.52; kappa = 0.28 / 0.48 = 7/12
    assert kappa(a, b) == pytest.approx(7 / 12)


def test_kappa_edge_cases() -> None:
    assert kappa(["y", "y"], ["y", "y"]) is None  # one label everywhere: undefined
    assert kappa(["y", "n"], ["n", "y"]) == pytest.approx(-1.0)
    assert kappa([], []) is None
    with pytest.raises(ValueError):
        kappa(["y"], [])


def test_bootstrap_is_deterministic_and_brackets_the_estimate() -> None:
    a = ["y"] * 30 + ["n"] * 30
    b = ["y"] * 25 + ["n"] * 5 + ["n"] * 25 + ["y"] * 5
    ci = bootstrap(a, b)
    assert ci == bootstrap(a, b)
    assert ci is not None and ci[0] < (kappa(a, b) or 0) < ci[1]


def test_landis_koch_words() -> None:
    assert [landis_koch(k) for k in (-0.1, 0.1, 0.3, 0.5, 0.7, 0.9)] == [
        "poor", "slight", "fair", "moderate", "substantial", "almost perfect",
    ]  # fmt: skip


# --- sample and report -----------------------------------------------------------------


def ans(i: str, stratum: str, hit: int | None, **kw: Any) -> dict[str, Any]:
    return {"id": i, "stratum": stratum, "hit_rank": hit, "prompt_s": 1.0, "answer_s": 2.0,
            "answer_tokens": 80, "done_reason": "stop", "quotes_removed": 0, "answer": "x",
            **kw}  # fmt: skip


def test_sample_takes_hits_only_and_is_seeded() -> None:
    pool = [ans(f"r{i}", "expert-ruling", 1 if i % 2 else None) for i in range(20)]
    pool += [ans("deep", "expert-ruling", 7)]  # in the top 20, not the top 5
    ids = answers.draw(pool, {"expert-ruling": 5}, seed=1)
    assert ids == answers.draw(pool, {"expert-ruling": 5}, seed=1)
    assert len(ids) == 5 and all(int(i[1:]) % 2 for i in ids)


def test_report_conditions_on_hits_and_computes_kappa(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    rows = [ans("a", "expert-ruling", 1), ans("b", "expert-ruling", 2),
            ans("c", "expert-ruling", None), ans("d", "expert-ruling", 3)]  # fmt: skip
    (tmp_path / "answers.json").write_text(json.dumps({
        "generator": {"model": "g", "digest": "d" * 12, "think": False, "temperature": 0,
                      "seed": 1, "num_ctx": 8192, "max_tokens": 400},
        "template_sha256": "t" * 12, "retrieval": {"method": "as-of", "k": 5},
        "placement": {"gpu_fraction": 1.0, "cpu_only": False}, "answers": rows,
    }))  # fmt: skip
    verdicts = {"a": "correct", "b": "incorrect", "c": "correct", "d": "correct"}
    (tmp_path / "judgments-g.json").write_text(json.dumps({
        "judge_model": "g", "judge_digest": "d" * 12,
        "judgments": [{"id": k, "verdict": v, "reason": ""} for k, v in verdicts.items()],
    }))  # fmt: skip
    review = tmp_path / "review.yaml"
    review.write_text(json.dumps({"run": tmp_path.name, "items": [
        {"id": "a", "verdict": "correct"}, {"id": "b", "verdict": "incorrect"},
        {"id": "d", "verdict": "incorrect"},
    ]}))  # fmt: skip
    monkeypatch.setattr(answers, "REVIEW", review)
    text = "\n".join(answers.report(tmp_path))
    # Given a hit: a, b, d -> 2 of 3 correct. Unconditioned: 3 of 4.
    assert "| expert-ruling | 2/3 = 67%" in text and "| 3/4 = 75%" in text
    assert "Judge against hand labels (3 answers)" in text
    assert "hand 33%, judge 67%" in text


def test_no_kappa_against_another_runs_labels(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    review = tmp_path / "review.yaml"
    review.write_text(
        json.dumps({"run": "answers-x", "items": [{"id": "a", "verdict": "correct"}]})
    )
    monkeypatch.setattr(answers, "REVIEW", review)
    assert "No kappa here" in answers.agreement_lines({"a": "correct"}, "agent-y")[0]


def test_identical_counts_prompts_with_one_distinct_output() -> None:
    from rb_errata.determinism import identical

    assert identical([["a", "a", "a"], ["a", "b", "a"], ["c", "c", "c"]]) == 2
