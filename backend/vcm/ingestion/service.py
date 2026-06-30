"""Ingestion orchestration: raw source -> object store + `documents` + `chunks` (plan/02).

Ties the object store, parser, and chunker together and persists a `Document` plus its
`Chunk` rows. The ORM-row builders are pure (no DB), so the mapping is unit-testable; the
caller owns the transaction (commit).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import httpx
from sqlalchemy.orm import Session

from vcm.config import get_settings
from vcm.db.models import Chunk, Document
from vcm.ingestion.edgar import FetchedDocument, fetch_latest_10k
from vcm.ingestion.store import ObjectStore
from vcm.models.enums import SourceType
from vcm.parsing.chunk import TextChunk, chunk_text
from vcm.parsing.parse import parse_document

_CONTENT_TYPE_SUFFIX = {
    "text/html": ".html",
    "application/xhtml+xml": ".html",
    "text/plain": ".txt",
    "text/markdown": ".md",
    "application/pdf": ".pdf",
}


@dataclass(frozen=True)
class IngestResult:
    document: Document
    chunk_count: int


def _suffix(filename: str | None, content_type: str | None) -> str:
    if filename and "." in filename:
        return Path(filename).suffix
    ct = (content_type or "").split(";")[0].strip().lower()
    return _CONTENT_TYPE_SUFFIX.get(ct, "")


def build_document(
    *,
    source_type: SourceType,
    title: str,
    storage_key: str,
    sha256: str,
    publisher: str | None = None,
    url: str | None = None,
    accession_number: str | None = None,
    published_at: datetime | None = None,
) -> Document:
    return Document(
        source_type=source_type,
        title=title,
        publisher=publisher,
        published_at=published_at,
        url=url,
        accession_number=accession_number,
        storage_path=storage_key,
        sha256=sha256,
    )


def build_chunk(document_id: object, chunk: TextChunk) -> Chunk:
    return Chunk(
        document_id=document_id,
        ordinal=chunk.ordinal,
        text=chunk.text,
        char_start=chunk.char_start,
        char_end=chunk.char_end,
        token_count=chunk.token_count,
    )


def ingest_document(
    session: Session,
    *,
    raw: bytes,
    source_type: SourceType,
    title: str,
    content_type: str | None = None,
    filename: str | None = None,
    publisher: str | None = None,
    url: str | None = None,
    accession_number: str | None = None,
    published_at: datetime | None = None,
    store: ObjectStore | None = None,
    target_chars: int | None = None,
) -> IngestResult:
    """Store the raw bytes, parse + chunk them, and persist `documents` + `chunks`.

    Flushes (to assign ids) but does not commit — the caller owns the transaction.
    """
    store = store or ObjectStore()
    target = target_chars if target_chars is not None else get_settings().chunk_target_chars

    obj = store.save(raw, suffix=_suffix(filename, content_type))
    text = parse_document(raw, content_type=content_type, filename=filename)
    chunks = chunk_text(text, target_chars=target)

    document = build_document(
        source_type=source_type,
        title=title,
        storage_key=obj.key,
        sha256=obj.sha256,
        publisher=publisher,
        url=url,
        accession_number=accession_number,
        published_at=published_at,
    )
    session.add(document)
    session.flush()  # assign document.id
    for chunk in chunks:
        session.add(build_chunk(document.id, chunk))
    session.flush()
    return IngestResult(document=document, chunk_count=len(chunks))


def ingest_upload(
    session: Session,
    *,
    data: bytes,
    filename: str | None,
    source_type: SourceType,
    title: str,
    content_type: str | None = None,
    publisher: str | None = None,
    url: str | None = None,
    store: ObjectStore | None = None,
) -> IngestResult:
    """Ingest a manually uploaded transcript / deck / document."""
    return ingest_document(
        session,
        raw=data,
        source_type=source_type,
        title=title,
        content_type=content_type,
        filename=filename,
        publisher=publisher,
        url=url,
        store=store,
    )


def ingest_edgar_10k(
    session: Session,
    *,
    ticker_or_cik: str,
    form: str = "10-K",
    client: httpx.Client | None = None,
    store: ObjectStore | None = None,
) -> IngestResult:
    """Fetch the latest 10-K for a ticker/CIK from SEC EDGAR and ingest it."""
    fetched: FetchedDocument = fetch_latest_10k(ticker_or_cik, form=form, client=client)
    return ingest_document(
        session,
        raw=fetched.raw,
        source_type=SourceType.SEC_filing,
        title=fetched.title,
        content_type=fetched.content_type,
        filename=fetched.filename,
        url=fetched.url,
        accession_number=fetched.accession_number,
        published_at=fetched.published_at,
        store=store,
    )
