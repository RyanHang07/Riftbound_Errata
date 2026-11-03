"""Slice 18 contracts: the registry refuses what could mis-ingest; updates are found."""

from __future__ import annotations

from typing import Any

import pytest
import yaml

from rb_errata.ingest import sources, updates
from rb_errata.ingest.sources import CORE_RULES

ROW: dict[str, Any] = {
    "version": "1.1", "name": "Origins", "sha1": "a" * 40, "urls": ["https://x"],
    "patch_notes": "https://playriftbound.com/x", "provenance": "cdn-verified",
}  # fmt: skip


def test_registry_keeps_the_ingested_pins() -> None:
    # Moving the registry to YAML must not change a single pinned byte.
    assert {d.version: d.sha1 for d in CORE_RULES[:5]} == {
        "1.0": "c780858c1621672aea0dc6b454e9233f5a43d000",
        "1.1": "dbc96e31db9d0257b0791aafb6dbb0cd219d3efb",
        "1.2": "572377fcaa704a05f72eb42c104079d3b3bcf740",
        "1.3": "7affc578516386a973dffcc8132350856c5a104c",
        "1.4": "e9ac8e3d33e0f78cef296f5945aba7bc1313b086",
    }


@pytest.mark.parametrize(
    ("change", "match"),
    [
        ({"version": "1.x"}, "MAJOR.MINOR"),
        ({"sha1": "ABC"}, "sha1"),
        ({"provenance": "trust-me"}, "provenance"),
        ({"urls": []}, "no urls"),
    ],
)
def test_registry_refuses_bad_rows(change: dict[str, Any], match: str) -> None:
    with pytest.raises(ValueError, match=match):
        sources.parse([{**ROW, **change}])


def test_registry_refuses_duplicates_and_disorder() -> None:
    with pytest.raises(ValueError, match="duplicate"):
        sources.parse([ROW, ROW])
    with pytest.raises(ValueError, match="out of order"):
        sources.parse([{**ROW, "version": "1.10"}, {**ROW, "version": "1.9"}])


def test_versions_sort_numerically() -> None:
    # 1.10 comes after 1.9; a string sort would call this registry out of order.
    docs = sources.parse([{**ROW, "version": v} for v in ("1.9", "1.10")])
    assert [d.version for d in docs] == ["1.9", "1.10"]


def test_missing_versions_from_the_mirror_manifest() -> None:
    manifest = {"coreRules": {"versions": {"1.4": {"name": "Vendetta"}, "1.5": {"name": "Radiance"},
                                           "1.10": {}}}}  # fmt: skip
    assert updates.missing_versions(["1.4"], manifest) == [("1.5", "Radiance"), ("1.10", "")]


def test_hub_links_finds_unregistered_pdfs_and_notes() -> None:
    html = (
        '<a href="https://cmsassets.rgpub.io/sanity/files/dsfx7636/news_live/'
        f'{"b" * 40}.pdf">Core Rules</a>'
        f'<a href="https://cmsassets.rgpub.io/sanity/files/dsfx7636/news_live/{"a" * 40}.pdf">'
        '<a href="/en-us/news/announcements/core-rules-legacy-patch-notes/">notes</a>'
    )
    pdfs, notes = updates.hub_links(html, {"a" * 40})
    assert pdfs == ["b" * 40]
    assert notes == [
        "https://playriftbound.com/en-us/news/announcements/core-rules-legacy-patch-notes/"
    ]


def test_appended_entry_keeps_the_registry_valid() -> None:
    text = sources.REGISTRY.read_text() + updates.entry_block(
        "9.0", "Legacy", "c" * 40, ["https://m"], "https://playriftbound.com/n", "cdn-verified"
    )
    docs = sources.parse(yaml.safe_load(text))
    assert (docs[-1].version, docs[-1].name, docs[-1].urls) == ("9.0", "Legacy", ("https://m",))
    assert "# Every Core Rules version" in text  # comments survive an append


@pytest.mark.parametrize(
    ("version", "notes", "match"),
    [
        ("1.4", "https://playriftbound.com/x", "already reaches"),
        ("1.0", "https://playriftbound.com/x", "already reaches"),
        ("v2", "https://playriftbound.com/x", "MAJOR.MINOR"),
        ("9.0", "https://riftbound.gg/notes", "Riot's patch notes"),
    ],
)
def test_add_version_refuses_bad_input(version: str, notes: str, match: str) -> None:
    with pytest.raises(SystemExit, match=match):
        updates.check_new(version, notes, CORE_RULES)


def test_integrate_stops_before_ingest_without_an_effective_date(
    tmp_path: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    import json
    import subprocess
    from types import SimpleNamespace

    ran: list[tuple[str, ...]] = []

    def fake_run(cmd: list[str], **_: Any) -> Any:
        ran.append(tuple(cmd[3:]))
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(subprocess, "run", fake_run)
    dates = tmp_path / "dates.json"
    dates.write_text(json.dumps([{"version": "9.0", "status": "unknown", "reason": "ambiguous"}]))
    assert updates.integrate("9.0", "https://playriftbound.com/x", dates) == 1
    assert [r[0] for r in ran] == ["add-version", "fetch", "dates"]  # never ingest

    ran.clear()
    dates.write_text(json.dumps([{"version": "9.0", "status": "known", "effective": "2030-01-01",
                                  "basis": "stated"}]))  # fmt: skip
    assert updates.integrate("9.0", "https://playriftbound.com/x", dates) == 0
    assert [r[0] for r in ran] == ["add-version", "fetch", "dates", "version-impact", "ingest",
                                   "recall", "mcp-check"]  # fmt: skip
