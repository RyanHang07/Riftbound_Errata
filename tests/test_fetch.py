import hashlib
from pathlib import Path

import httpx

from rb_errata.ingest.fetch import fetch_pdf
from rb_errata.ingest.sources import CORE_RULES, RulesDoc

GOOD = b"%PDF-1.7 the right bytes"
DOC = RulesDoc(
    "core", "9.9", hashlib.sha1(GOOD).hexdigest(),
    ("https://cdn.test/a.pdf", "https://mirror.test/a.pdf"), None, "test",
)  # fmt: skip


def client(responses: dict[str, tuple[int, bytes]]) -> httpx.Client:
    def handle(req: httpx.Request) -> httpx.Response:
        code, body = responses.get(str(req.url), (404, b""))
        return httpx.Response(code, content=body)

    return httpx.Client(transport=httpx.MockTransport(handle))


def test_wrong_bytes_are_refused_and_the_next_url_is_tried(tmp_path: Path) -> None:
    c = client({DOC.urls[0]: (200, b"tampered"), DOC.urls[1]: (200, GOOD)})
    line, url = fetch_pdf(DOC, c, tmp_path)
    assert url == DOC.urls[1] and line.startswith("obtained")
    assert (tmp_path / DOC.filename).read_bytes() == GOOD


def test_no_matching_source_fails_and_leaves_nothing_behind(tmp_path: Path) -> None:
    line, url = fetch_pdf(DOC, client({DOC.urls[0]: (200, b"tampered")}), tmp_path)
    assert line.startswith("FAILED") and url == ""
    assert list(tmp_path.iterdir()) == []


def test_every_source_is_pinned_and_mirror_urls_are_pinned_to_a_commit() -> None:
    for doc in CORE_RULES:
        assert len(doc.sha1) == 40
        assert all("/main/" not in u for u in doc.urls)
