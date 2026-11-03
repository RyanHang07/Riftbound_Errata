"""Slice 13: a confidence score from measurable signals, and whether it is calibrated.

A21: computed from signals anyone can recompute, never from the model's own
claim of certainty. Each answer's signals go through a logistic regression
fitted to the judge's verdicts. Two outputs:

- Out-of-fold probabilities (5 folds, seeded): every answer is scored by a
  model that never saw it. These alone are used for the calibration verdict.
- A model fitted on every answer, saved as `confidence.json` in the run
  folder (coefficients, scaling, metrics; numbers only), for the agent
  (slice 14) to score new answers with.

Pass rule, fixed before any answer existed (docs/RECALL.md, slice 13):
calibrated only if expected calibration error over 5 equal-count bins is at
most 0.10 AND the Brier score beats always predicting the base rate. The
labels are the judge's, so the verdict is only as good as slice 11's kappa.
"""

from __future__ import annotations

import json
import math
import random
import re
from datetime import date
from pathlib import Path
from typing import Any

import numpy as np

from rb_errata.labels.review import load_questions

FEATURES = (
    "top_distance",
    "margin",
    "top_in_effect",
    "versions_disagree",
    "cites_any",
    "cites_only_retrieved",
    "cites_only_in_effect",
    "abstains",
    "log_answer_tokens",
)
MAX_ECE = 0.10
BINS = 5
FOLDS = 5
SEED = 20261103
L2 = 1.0
_CITE = re.compile(r"core@(\d+\.\d+):(\d{3}(?:\.[0-9a-z]+)*)")
_ABSTAIN = re.compile(
    r"\b(do(?:es)? not|don't|doesn't) (answer|contain|cover|address|specify|say|mention)"
    r"|not (enough|sufficient) information|cannot be determined|no information",
    re.IGNORECASE,
)


def _in_effect(version: str, day: date, windows: dict[str, tuple[date, date | None]]) -> bool:
    if version not in windows:
        return False
    start, end = windows[version]
    return start <= day and (end is None or day < end)


def signals(
    a: dict[str, Any], as_of: date, windows: dict[str, tuple[date, date | None]]
) -> dict[str, float]:
    """The A21 signals for one answer row. Pure; every value recomputable from the run."""
    d = a["distances"]
    versions = {r.split(":", 1)[0].split("@", 1)[1] for r in a["retrieved"]}
    top_version = a["retrieved"][0].split(":", 1)[0].split("@", 1)[1] if a["retrieved"] else ""
    cited = _CITE.findall(a["answer"])
    retrieved = set(a.get("retrieved_refs", []))
    return {
        "top_distance": d[0] if d else 1.0,
        "margin": d[1] - d[0] if len(d) > 1 else 0.0,
        "top_in_effect": float(_in_effect(top_version, as_of, windows)),
        "versions_disagree": float(len(versions) > 1),
        "cites_any": float(bool(cited)),
        "cites_only_retrieved": float(
            bool(cited) and all(f"core@{v}:{n}" in retrieved for v, n in cited)
        ),
        "cites_only_in_effect": float(
            bool(cited) and all(_in_effect(v, as_of, windows) for v, _ in cited)
        ),
        "abstains": float(bool(_ABSTAIN.search(a["answer"]))),
        "log_answer_tokens": math.log1p(a["answer_tokens"]),
    }


# --- logistic regression, numpy only ------------------------------------------------


def fit(x: np.ndarray, y: np.ndarray) -> dict[str, Any]:
    """L2-regularised logistic regression by Newton's method on standardised
    features. Constant columns get zero weight instead of a division by zero."""
    mean, std = x.mean(axis=0), x.std(axis=0)
    std = np.where(std == 0, 1.0, std)
    z = np.hstack([np.ones((len(x), 1)), (x - mean) / std])
    w = np.zeros(z.shape[1])
    penalty = np.eye(z.shape[1]) * L2
    penalty[0, 0] = 0.0  # the intercept is not shrunk
    for _ in range(50):
        p = 1 / (1 + np.exp(-z @ w))
        grad = z.T @ (p - y) + penalty @ w
        hess = (z.T * (p * (1 - p))) @ z + penalty
        step = np.linalg.solve(hess, grad)
        w -= step
        if np.abs(step).max() < 1e-8:
            break
    return {"weights": w.tolist(), "mean": mean.tolist(), "std": std.tolist()}


def predict(model: dict[str, Any], x: np.ndarray) -> np.ndarray:
    w, mean, std = (np.asarray(model[k]) for k in ("weights", "mean", "std"))
    z = np.hstack([np.ones((len(x), 1)), (x - mean) / std])
    out: np.ndarray = 1 / (1 + np.exp(-z @ w))
    return out


def out_of_fold(x: np.ndarray, y: np.ndarray, folds: int = FOLDS, seed: int = SEED) -> np.ndarray:
    idx = list(range(len(y)))
    random.Random(seed).shuffle(idx)
    probs = np.zeros(len(y))
    for f in range(folds):
        test = idx[f::folds]
        train = [i for i in idx if i not in set(test)]
        probs[test] = predict(fit(x[train], y[train]), x[test])
    return probs


# --- calibration ---------------------------------------------------------------------


def calibration(probs: np.ndarray, y: np.ndarray, bins: int = BINS) -> list[dict[str, float]]:
    """Equal-count bins, lowest confidence first: mean predicted vs observed."""
    order = np.argsort(probs, kind="stable")
    out = []
    for chunk in np.array_split(order, bins):
        if len(chunk):
            out.append({"n": float(len(chunk)), "predicted": float(probs[chunk].mean()),
                        "observed": float(y[chunk].mean())})  # fmt: skip
    return out


def ece(table: list[dict[str, float]]) -> float:
    total = sum(b["n"] for b in table)
    return sum(b["n"] / total * abs(b["predicted"] - b["observed"]) for b in table)


def brier(probs: np.ndarray, y: np.ndarray) -> float:
    return float(np.mean((probs - y) ** 2))


# --- the run -------------------------------------------------------------------------


def _windows() -> dict[str, tuple[date, date | None]]:
    from rb_errata import tools

    return {v: (w.valid_from, w.valid_to) for v, w in tools.windows().items()}


def evaluate(run_dir: Path, judge_file: Path) -> list[str]:
    snap = json.loads((run_dir / "answers.json").read_text())
    verdicts = {r["id"]: r["verdict"] for r in json.loads(judge_file.read_text())["judgments"]}
    questions = {q["id"]: q for q in load_questions()}
    windows = _windows()
    judged = {i for i, v in verdicts.items() if v != "unparsed"}
    rows = [a for a in snap["answers"] if a["id"] in questions and a["id"] in judged]
    if not rows or "distances" not in rows[0]:
        raise SystemExit("this answers run predates slice 13's signals; rerun `make answers`")
    sig = [signals(a, date.fromisoformat(str(questions[a["id"]]["as_of"])), windows) for a in rows]
    x = np.array([[s[f] for f in FEATURES] for s in sig])
    y = np.array([float(verdicts[a["id"]] == "correct") for a in rows])
    probs = out_of_fold(x, y)
    table = calibration(probs, y)
    e, b = ece(table), brier(probs, y)
    base = brier(np.full(len(y), y.mean()), y)
    ok = e <= MAX_ECE and b < base
    model = fit(x, y)
    (run_dir / "confidence.json").write_text(json.dumps({
        "features": list(FEATURES), **model, "judge": judge_file.name, "n": len(y),
        "ece": round(e, 4), "brier": round(b, 4), "brier_base_rate": round(base, 4),
        "calibrated": bool(ok),
    }, indent=1) + "\n")  # fmt: skip
    constant = [f for i, f in enumerate(FEATURES) if np.ptp(x[:, i]) == 0]
    weights = dict(zip(FEATURES, model["weights"][1:], strict=True))
    lines = [
        f"# Confidence for {run_dir.name}",
        "",
        f"Labels: {judge_file.name} ({len(y)} answers, {y.mean():.0%} correct). Out-of-fold "
        f"probabilities, {FOLDS} folds, seed {SEED}. Usable only if that judge's kappa is.",
        "",
        f"**{'Calibrated' if ok else 'Uncalibrated'}.** ECE {e:.3f} (pass: at most {MAX_ECE}); "
        f"Brier {b:.3f} against {base:.3f} for always predicting the base rate "
        f"(skill {1 - b / base:+.2f}).",
        "",
        "| bin (low to high) | answers | mean confidence | observed correct |",
        "|---|---|---|---|",
        *[f"| {i + 1} | {int(t['n'])} | {t['predicted']:.0%} | {t['observed']:.0%} |"
          for i, t in enumerate(table)],
        "",
        f"Top bin minus bottom bin, observed: {table[-1]['observed'] - table[0]['observed']:+.0%}.",
        "",
        "## Signal weights (model fitted on all answers; standardised, so comparable)",
        "",
        "| signal | weight | positive in |",
        "|---|---|---|",
        *[f"| {f} | {weights[f]:+.2f} | "
          + ("constant: no signal" if f in constant
             else f"{int(x[:, i].astype(bool).sum())} of {len(y)}"
             if set(np.unique(x[:, i])) <= {0.0, 1.0} else "continuous") + " |"
          for i, f in enumerate(FEATURES)],
    ]  # fmt: skip
    (run_dir / "confidence.md").write_text("\n".join(lines) + "\n")
    return lines


def score(model: dict[str, Any], sig: dict[str, float]) -> float:
    """One answer's confidence from a saved model (the agent's use)."""
    return float(predict(model, np.array([[sig[f] for f in model["features"]]]))[0])
