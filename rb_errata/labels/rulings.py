"""Convert the community rulings (A21) into labelled questions.

Source: github.com/ChristianIvicevic/riftboundfaq, `content/(rulings)/`,
CC BY-SA 4.0, by Christian "Near" Ivicevic. Each .mdx file has frontmatter
(title, createdAt, reviewedCoreRulesVersion, authors) and one `## Question?
[#anchor]` section per question, whose answer cites rules as
`<Rule number="419.4.a" />`.

The answer prose is kept (the licence allows it with attribution and the same
licence) because slice 6 needs a reference answer to judge against. MDX
components are rendered to plain text by a fixed table; an unknown component
raises instead of being dropped, so new markup cannot silently lose words.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

REPO = "ChristianIvicevic/riftboundfaq"
# Pinned: labels must not change because the upstream site was edited.
COMMIT = "816d3b32d32a9966fc73367efb690fcbb4c195ca"
RULINGS_DIR = "content/(rulings)"

_HEADING = re.compile(r"^## (?P<q>.+?) \[#(?P<anchor>[\w-]+)\]\s*$")
_RULE = re.compile(r'<Rule number="(?P<n>[0-9a-z.]+)"\s*/>')
_FAQ = re.compile(r"\]\(https://playriftbound\.com/[^)]*faq[^)]*\)", re.IGNORECASE)

# Self-closing keyword components render as the keyword's printed name.
_KEYWORD_NAMES = {"QuickDraw": "Quick-Draw"}


def _render(text: str) -> str:
    """MDX body to plain text. Raises on a component it does not know."""
    t = _RULE.sub(lambda m: f" [{m.group('n')}]", text)
    t = re.sub(r'<Card name="([^"]+)"\s*/>', r"\1", t)
    t = re.sub(r'<Term item="[^"]*">(.*?)</Term>', r"\1", t, flags=re.DOTALL)
    t = re.sub(r"<Energy value=\{(\d+)\}\s*/>", r"[\1]", t)
    t = re.sub(r'<Callout type="[^"]*" title="([^"]*)">', r"Note (\1):", t)
    t = re.sub(r"</?Callout>", "", t)
    t = re.sub(r"<Step>", "- ", t)
    t = re.sub(r"</?Steps?>", "", t)
    t = re.sub(r"<([A-Z][A-Za-z]*)\s*/>", lambda m: _KEYWORD_NAMES.get(m.group(1), m.group(1)), t)
    t = re.sub(r"\[([^\]]+)\]\((?:https?://)[^)]+\)", r"\1", t)  # markdown links -> text
    leftover = re.search(r"</?[A-Z][A-Za-z]*[^>]*>", t)
    if leftover:
        raise ValueError(f"unknown MDX component: {leftover.group(0)[:60]}")
    lines = [" ".join(line.split()) for line in t.splitlines()]
    return "\n".join(line for line in lines if line).strip()


@dataclass
class Ruling:
    id: str
    category: str  # cards | general-rules | mechanics
    question: str
    answer: str
    answer_short: str  # "yes" | "no" | "other"
    rule_numbers: list[str]
    faq_backed: bool  # the answer leans on an official Riot FAQ
    path: str
    anchor: str
    title: str
    created: str
    reviewed_version: str
    authors: list[str] = field(default_factory=list)

    @property
    def url(self) -> str:
        return f"https://github.com/{REPO}/blob/{COMMIT}/{self.path}#{self.anchor}"


def parse_file(path: Path, root: Path) -> list[Ruling]:
    raw = path.read_text()
    _, front, body = raw.split("---", 2)
    meta = yaml.safe_load(front)
    rel = path.relative_to(root).as_posix()
    category = path.parent.name
    out: list[Ruling] = []
    current: tuple[str, str] | None = None
    lines: list[str] = []

    def flush() -> None:
        if current is None:
            return
        q, anchor = current
        section = "\n".join(lines)
        numbers = list(dict.fromkeys(m.group("n") for m in _RULE.finditer(section)))
        answer = _render(section)
        first = answer.splitlines()[0].lower().rstrip(".") if answer else ""
        out.append(
            Ruling(
                id=f"r-{path.stem}-{anchor}",
                category=category,
                question=_render(q),
                answer=answer,
                answer_short=first if first in {"yes", "no"} else "other",
                rule_numbers=numbers,
                faq_backed=bool(_FAQ.search(section)),
                path=rel,
                anchor=anchor,
                title=str(meta["title"]),
                created=str(meta["createdAt"]),
                reviewed_version=str(meta["reviewedCoreRulesVersion"]),
                authors=[a["name"] for a in meta.get("authors", [])],
            )
        )

    for line in body.splitlines():
        m = _HEADING.match(line)
        if m:
            flush()
            current, lines = (m.group("q"), m.group("anchor")), []
        elif line.startswith("## "):
            raise ValueError(f"{rel}: question heading without an anchor: {line[:60]}")
        elif current is not None:
            lines.append(line)
    flush()
    return out


def parse_all(clone: Path) -> list[Ruling]:
    base = clone / RULINGS_DIR
    rulings = [r for p in sorted(base.glob("*/*.mdx")) for r in parse_file(p, clone)]
    ids = [r.id for r in rulings]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate ruling ids")
    return rulings
