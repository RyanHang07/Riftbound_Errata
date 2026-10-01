"""PDF text extraction and the printed "Last Updated" date."""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path

import pypdfium2 as pdfium  # type: ignore[import-untyped]  # ships no type stubs

# Both formats appear in Riot's own documents (SPIKE_1, finding 3):
# "2026-03-30" and "7/16/2026". Anything else is refused, never guessed.
_PRINTED = re.compile(r"Last Updated:?\s*(\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{4})")


def extract_text(path: Path) -> str:
    pdf = pdfium.PdfDocument(path)
    try:
        # \r\n from pdfium becomes \n; rule parsing works line by line.
        return "\n".join(page.get_textpage().get_text_bounded() for page in pdf).replace("\r", "")
    finally:
        pdf.close()


def parse_date(raw: str) -> date:
    """Parse one of the two date formats Riot prints. Raises on anything else."""
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw):
        return date.fromisoformat(raw)
    m = re.fullmatch(r"(\d{1,2})/(\d{1,2})/(\d{4})", raw)
    if m:
        # US order. Riot is a US company and "7/16/2026" has no 16th month,
        # but a value like "4/5/2026" is ambiguous in principle; the printed
        # dates seen so far are all unambiguous, and the known-dates test
        # would catch a misread.
        return date(int(m.group(3)), int(m.group(1)), int(m.group(2)))
    raise ValueError(f"unrecognised date format: {raw!r}")


def printed_date(text: str) -> date:
    """The date printed near the top of the first page."""
    m = _PRINTED.search(text[:2000])
    if not m:
        raise ValueError("no 'Last Updated' date near the start of the document")
    return parse_date(m.group(1))
