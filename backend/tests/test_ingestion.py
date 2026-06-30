"""Offline tests for ingestion: object store, EDGAR parsing, and persistence (SQLite)."""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from vcm.db.base import Base
from vcm.db.models import Chunk, Document
from vcm.ingestion.edgar import (
    FilingRef,
    IngestionError,
    archive_url,
    normalize_cik,
    pick_latest_filing,
    resolve_cik,
)
from vcm.ingestion.service import ingest_document
from vcm.ingestion.store import ObjectStore
from vcm.models.enums import SourceType

# --------------------------------------------------------------------------- #
# ObjectStore
# --------------------------------------------------------------------------- #


def test_object_store_is_content_addressed_and_idempotent(tmp_path: Path) -> None:
    store = ObjectStore(tmp_path)
    a = store.save(b"hello world", suffix=".txt")
    b = store.save(b"hello world", suffix="txt")  # same content, suffix w/o dot
    assert a.sha256 == b.sha256
    assert a.key == b.key  # same key -> stored once
    assert a.path.read_bytes() == b"hello world"
    assert a.key.startswith(a.sha256[:2] + "/")  # sharded by first 2 hex chars
    assert a.size == 11


def test_object_store_distinct_content(tmp_path: Path) -> None:
    store = ObjectStore(tmp_path)
    assert store.save(b"one").sha256 != store.save(b"two").sha256


# --------------------------------------------------------------------------- #
# EDGAR pure helpers
# --------------------------------------------------------------------------- #


def test_normalize_cik() -> None:
    assert normalize_cik("1045810") == "0001045810"
    assert normalize_cik("CIK0000789019") == "0000789019"
    assert normalize_cik("NVDA") is None


def test_resolve_cik_from_ticker_map() -> None:
    ticker_map = {
        "0": {"cik_str": 1045810, "ticker": "NVDA", "title": "NVIDIA CORP"},
        "1": {"cik_str": 789019, "ticker": "MSFT", "title": "MICROSOFT CORP"},
    }
    assert resolve_cik("nvda", ticker_map=ticker_map) == "0001045810"
    assert resolve_cik("0000789019", ticker_map=ticker_map) == "0000789019"  # already a CIK
    with pytest.raises(IngestionError):
        resolve_cik("ZZZZ", ticker_map=ticker_map)


def test_pick_latest_filing_returns_first_matching_form() -> None:
    submissions = {
        "name": "NVIDIA CORP",
        "filings": {
            "recent": {
                "form": ["8-K", "10-K", "10-Q", "10-K"],
                "accessionNumber": ["0-0", "0001045810-25-000001", "0-2", "0001045810-24-000010"],
                "primaryDocument": ["a.htm", "nvda-10k.htm", "c.htm", "old.htm"],
                "filingDate": ["2025-03-01", "2025-02-21", "2024-11-20", "2024-02-21"],
            }
        },
    }
    ref = pick_latest_filing(submissions, form="10-K")
    assert ref.accession_number == "0001045810-25-000001"  # newest-first -> first match
    assert ref.primary_document == "nvda-10k.htm"
    assert ref.filing_date == "2025-02-21"


def test_pick_latest_filing_missing_form_raises() -> None:
    with pytest.raises(IngestionError):
        pick_latest_filing({"filings": {"recent": {"form": ["8-K"]}}}, form="10-K")


def test_archive_url_strips_padding_and_dashes() -> None:
    ref = FilingRef(
        accession_number="0001045810-25-000001",
        primary_document="nvda-10k.htm",
        filing_date="2025-02-21",
    )
    url = archive_url("0001045810", ref)
    assert url == (
        "https://www.sec.gov/Archives/edgar/data/1045810/000104581025000001/nvda-10k.htm"
    )


# --------------------------------------------------------------------------- #
# Persistence (SQLite — documents + chunks only)
# --------------------------------------------------------------------------- #


@pytest.fixture
def db_session() -> Session:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine, tables=[Document.__table__, Chunk.__table__])
    with sessionmaker(engine)() as session:
        yield session


def test_ingest_document_persists_document_and_chunks(db_session: Session, tmp_path: Path) -> None:
    raw = (
        b"NVIDIA's data-center GPUs use HBM3E from SK Hynix.\n\n"
        b"TSMC performs CoWoS advanced packaging for the H100.\n\n"
        b"Hyperscalers pre-pay to secure GPU allocation."
    )

    result = ingest_document(
        db_session,
        raw=raw,
        source_type=SourceType.transcript,
        title="Q4 call",
        filename="call.txt",
        url="https://example.com/call",
        store=ObjectStore(tmp_path),
        target_chars=60,
    )
    db_session.commit()

    docs = db_session.scalars(select(Document)).all()
    chunks = db_session.scalars(select(Chunk).order_by(Chunk.ordinal)).all()
    assert len(docs) == 1
    doc = docs[0]
    assert doc.source_type is SourceType.transcript
    assert doc.title == "Q4 call"
    assert len(doc.sha256) == 64
    assert doc.url == "https://example.com/call"
    assert result.chunk_count == len(chunks) >= 2
    assert [c.ordinal for c in chunks] == list(range(len(chunks)))
    assert all(c.document_id == doc.id for c in chunks)
    # the raw bytes are in the object store at the recorded key
    assert (tmp_path / doc.storage_path).read_bytes() == raw


def test_html_document_is_parsed_before_chunking(db_session: Session, tmp_path: Path) -> None:
    raw = (
        b"<html><body><p>Alpha co supplies Beta co.</p>"
        b"<p>Beta co serves the market.</p></body></html>"
    )
    ingest_document(
        db_session,
        raw=raw,
        source_type=SourceType.SEC_filing,
        title="10-K",
        content_type="text/html",
        filename="doc.htm",
        store=ObjectStore(tmp_path),
        target_chars=200,
    )
    db_session.commit()
    chunk = db_session.scalars(select(Chunk)).first()
    assert chunk is not None
    assert "<p>" not in chunk.text  # HTML was flattened
    assert "Alpha co supplies Beta co." in chunk.text
