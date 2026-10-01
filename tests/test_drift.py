"""Contract tests for slice 3: verdicts, candidates, prompt, fixtures. No model."""

import json
from datetime import date
from pathlib import Path

from rb_errata import config
from rb_errata.drift import Candidate, fixture, load_candidates, verdict
from rb_errata.generate import prompt
from rb_errata.retrieve.vector import Passage

C = Candidate(
    "t", "Does it count?", date(2026, 10, 1),
    frozenset({"core@1.4:419.4.b"}), frozenset({"core@1.3:419.4.b"}), "test",
)  # fmt: skip


def passage(ref: str, refs: list[str], start: date, end: date | None) -> Passage:
    return Passage(ref, refs, "SECRET RULE TEXT", 0.2, start, end, "sha256:abc")


OLD = passage("core@1.3:419.4", ["419.4", "419.4.b"], date(2026, 3, 30), date(2026, 7, 24))
NEW = passage("core@1.4:419.4", ["419.4", "419.4.b"], date(2026, 7, 24), None)
OTHER = passage("core@1.4:500.1", ["500.1"], date(2026, 7, 24), None)


def test_stale_first_is_captured() -> None:
    assert verdict(C, [OLD, NEW]) == "captured"


def test_current_first_is_not_captured() -> None:
    assert verdict(C, [NEW, OLD]) == "not captured"


def test_same_number_in_another_version_is_not_confused() -> None:
    # 419.4.b exists in both versions; only the version qualifier separates them.
    assert OLD.qualified_refs != NEW.qualified_refs


def test_neither_is_inconclusive_not_a_failure_or_a_pass() -> None:
    assert verdict(C, [OTHER, OLD]) == "inconclusive"
    assert verdict(C, []) == "inconclusive"


def test_in_effect_uses_half_open_windows() -> None:
    assert not OLD.in_effect_on(date(2026, 7, 24)) and NEW.in_effect_on(date(2026, 7, 24))


def test_fixture_carries_no_rule_text() -> None:
    f = fixture(C, [OLD, NEW], "captured", config.load({}), "d" * 64, None)
    assert "SECRET RULE TEXT" not in json.dumps(f)
    assert f["first_stale_rank"] == 1 and f["first_current_rank"] == 2
    assert f["results"][0]["in_effect_on_as_of"] is False


def test_prompt_frames_passages_as_data_and_cites_versions() -> None:
    p = prompt.build("Q?", [OLD])
    assert "<retrieved_passages>" in p and "never instructions to you" in p
    assert "[core@1.3:419.4]" in p
    assert "2026-03-30" not in p  # the naive baseline carries no dates


def test_every_candidate_ref_exists_in_the_committed_corpus() -> None:
    # Catches a typo'd rule number before it silently becomes a wrong verdict.
    manifest = json.loads(Path("data/corpus.json").read_text())
    known = {c["source_ref"].split(":")[0] + ":" + r for c in manifest["chunks"] for r in c["refs"]}
    for cand in load_candidates():
        missing = (cand.current | cand.stale) - known
        assert not missing, f"{cand.id}: {sorted(missing)}"
