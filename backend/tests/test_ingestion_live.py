"""Live, opt-in test: fetch a real 10-K from SEC EDGAR, parse it, and chunk it (no DB).

Skipped unless ``VCM_EDGAR_LIVE`` is set (SEC is rate-limited and needs network). Proves the
ingest -> parse -> chunk spine against real SEC data. Run with:

    VCM_EDGAR_LIVE=1 uv run pytest tests/test_ingestion_live.py -v
"""

from __future__ import annotations

import os

import pytest

from vcm.ingestion.edgar import fetch_latest_10k
from vcm.parsing import chunk_text, parse_document

pytestmark = pytest.mark.skipif(
    not os.getenv("VCM_EDGAR_LIVE"),
    reason="live SEC EDGAR fetch; set VCM_EDGAR_LIVE=1 to run",
)


def test_fetch_parse_chunk_real_10k() -> None:
    fetched = fetch_latest_10k("MSFT")
    assert fetched.raw, "expected non-empty 10-K document"
    assert fetched.accession_number
    assert fetched.cik == "0000789019"  # Microsoft
    assert "10-K" in fetched.title

    text = parse_document(fetched.raw, content_type=fetched.content_type, filename=fetched.filename)
    assert len(text) > 5000  # a real 10-K is large
    assert "<html" not in text.lower()  # HTML was flattened

    chunks = chunk_text(text)
    assert len(chunks) > 1
    assert all(text[c.char_start : c.char_end] == c.text for c in chunks)
