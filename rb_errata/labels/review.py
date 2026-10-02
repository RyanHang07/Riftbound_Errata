"""The sampled human review of the labelled set (A21, step 3).

The sample is drawn with a fixed seed, so anyone can reproduce which questions
were reviewed and check that none were picked by hand. Results go to
evals/review.yaml: one verdict per question, agree / disagree / unsure, three
states, and `unsure` is never counted as agreement.
"""

from __future__ import annotations

import random
from pathlib import Path
from typing import Any

import yaml

SEED = 20261002
# Stratified so every stratum is checked, roughly in proportion to the set
# (160 / 8 / 56), with the small FAQ stratum over-sampled so it is not zero.
# 60, not the 20 first planned: the user chose the larger review, which
# narrows the agreement interval from about +/-20 to about +/-12 points.
PLAN = {"expert-ruling": 40, "expert-ruling-faq": 4, "version-change": 16}
REVIEW = Path("evals/review.yaml")


def sample(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rng = random.Random(SEED)
    out = []
    for stratum, n in PLAN.items():
        pool = sorted((e for e in entries if e["stratum"] == stratum), key=lambda e: e["id"])
        out += rng.sample(pool, n)
    return out


def load_questions(path: Path = Path("evals/questions.yaml")) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = yaml.safe_load(path.read_text())
    return entries


def agreement(path: Path = REVIEW) -> tuple[int, int, int]:
    """(agree, disagree, unsure) from the committed review file."""
    rows = yaml.safe_load(path.read_text()) or []
    verdicts = [r["verdict"] for r in rows]
    bad = set(verdicts) - {"agree", "disagree", "unsure"}
    if bad:
        raise ValueError(f"unknown verdicts: {bad}")
    return verdicts.count("agree"), verdicts.count("disagree"), verdicts.count("unsure")
