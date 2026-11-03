"""Slice 13 contracts: signals recomputable, the fit learns, calibration is honest."""

from __future__ import annotations

import json
import random
from datetime import date
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from rb_errata import confidence

WINDOWS = {"1.3": (date(2026, 3, 30), date(2026, 7, 24)), "1.4": (date(2026, 7, 24), None)}


def row(answer: str, retrieved: list[str], distances: list[float], **kw: Any) -> dict[str, Any]:
    return {"answer": answer, "retrieved": retrieved, "distances": distances,
            "retrieved_refs": kw.pop("refs", []), "answer_tokens": 50, **kw}  # fmt: skip


def test_signals_from_one_answer() -> None:
    a = row("Yes [core@1.4:419.4.b].", ["core@1.4:419.4", "core@1.3:419.4"], [0.30, 0.42],
            refs=["core@1.4:419.4", "core@1.4:419.4.b"])  # fmt: skip
    s = confidence.signals(a, date(2026, 10, 1), WINDOWS)
    assert s["top_distance"] == 0.30 and s["margin"] == pytest.approx(0.12)
    assert s["top_in_effect"] == 1.0 and s["versions_disagree"] == 1.0
    assert (s["cites_any"], s["cites_only_retrieved"], s["cites_only_in_effect"]) == (1, 1, 1)
    assert s["abstains"] == 0.0


def test_citation_outside_retrieval_or_date_is_flagged() -> None:
    a = row("No [core@1.3:419.4.b]. The passages do not specify more.", ["core@1.4:1"], [0.3],
            refs=["core@1.4:1"])  # fmt: skip
    s = confidence.signals(a, date(2026, 10, 1), WINDOWS)
    assert (s["cites_only_retrieved"], s["cites_only_in_effect"], s["abstains"]) == (0, 0, 1)
    assert s["margin"] == 0.0  # one passage: no margin, not an error


def test_fit_learns_a_real_signal_and_ignores_a_constant() -> None:
    rng = random.Random(0)
    x = np.array([[rng.random(), 1.0] for _ in range(400)])
    y = np.array([float(rng.random() < 0.2 + 0.6 * v) for v, _ in x])
    model = confidence.fit(x, y)
    assert model["weights"][1] > 0.5  # the informative column
    assert model["weights"][2] == pytest.approx(0.0, abs=1e-9)  # the constant one


def test_calibration_numbers() -> None:
    probs = np.array([0.1, 0.1, 0.9, 0.9])
    y = np.array([0.0, 0.0, 1.0, 1.0])
    table = confidence.calibration(probs, y, bins=2)
    assert [(t["predicted"], t["observed"]) for t in table] == [(0.1, 0.0), (0.9, 1.0)]
    assert confidence.ece(table) == pytest.approx(0.1)
    assert confidence.brier(probs, y) == pytest.approx(0.01)


def _run(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, informative: bool) -> list[str]:
    rng = random.Random(1)
    rows, verdicts, questions = [], [], []
    for i in range(200):
        abstains = rng.random() < 0.3
        right = rng.random() < (0.15 if abstains and informative else 0.75 if informative else 0.5)
        text = "The passages do not say." if abstains else "Yes [core@1.4:1]."
        rows.append({"id": f"q{i}", **row(text, ["core@1.4:1"], [rng.random(), 0.9],
                                         refs=["core@1.4:1"])})  # fmt: skip
        verdicts.append({"id": f"q{i}", "verdict": "correct" if right else "incorrect"})
        questions.append({"id": f"q{i}", "as_of": "2026-10-01"})
    (tmp_path / "answers.json").write_text(json.dumps({"answers": rows}))
    judge = tmp_path / "judgments-x.json"
    judge.write_text(json.dumps({"judgments": verdicts}))
    monkeypatch.setattr(confidence, "load_questions", lambda: questions)
    monkeypatch.setattr(confidence, "_windows", lambda: WINDOWS)
    return confidence.evaluate(tmp_path, judge)


def test_informative_signals_pass_and_save_a_model(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    text = "\n".join(_run(tmp_path, monkeypatch, informative=True))
    assert "**Calibrated.**" in text
    saved = json.loads((tmp_path / "confidence.json").read_text())
    assert saved["calibrated"] is True and saved["features"] == list(confidence.FEATURES)
    sig = dict.fromkeys(confidence.FEATURES, 0.0)
    assert confidence.score(saved, {**sig, "abstains": 1.0}) < confidence.score(saved, sig)


def test_noise_is_not_called_skill(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Labels unrelated to every signal: the score must not beat the base rate.
    text = "\n".join(_run(tmp_path, monkeypatch, informative=False))
    assert "**Uncalibrated.**" in text
