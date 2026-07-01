"""Evidence store: content-addressed hashing + dedup on bind."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from vcm.db.models import Document, Evidence
from vcm.evidence import excerpt_hash, get_or_create_evidence
from vcm.models.enums import ExtractionMethod, SourceType


def _document() -> Document:
    return Document(
        source_type=SourceType.SEC_filing,
        title="NVDA 10-K",
        publisher="SEC",
        url="https://sec.gov/nvda",
        accession_number="0001045810-26-000021",
        storage_path="ab/abcd",
        sha256="0" * 64,
    )


def test_excerpt_hash_is_whitespace_insensitive() -> None:
    assert excerpt_hash("HBM3E  from\nSK Hynix") == excerpt_hash("HBM3E from SK Hynix")
    assert excerpt_hash("a") != excerpt_hash("b")
    assert len(excerpt_hash("x")) == 64


def test_get_or_create_evidence_persists_provenance(graph_session: Session) -> None:
    document = _document()
    graph_session.add(document)
    graph_session.flush()

    evidence = get_or_create_evidence(
        graph_session, excerpt="HBM3E is supplied by SK Hynix.", document=document
    )
    assert evidence.id is not None
    assert evidence.source_type is SourceType.SEC_filing
    assert evidence.title == "NVDA 10-K"
    assert evidence.url == "https://sec.gov/nvda"
    assert evidence.extraction_method is ExtractionMethod.llm
    assert evidence.excerpt_hash == excerpt_hash("HBM3E is supplied by SK Hynix.")


def test_get_or_create_evidence_dedups_by_hash(graph_session: Session) -> None:
    document = _document()
    graph_session.add(document)
    graph_session.flush()

    first = get_or_create_evidence(graph_session, excerpt="Same quote.", document=document)
    # a whitespace-different but semantically identical excerpt hashes the same -> reused
    second = get_or_create_evidence(graph_session, excerpt="Same   quote.", document=document)
    assert first.id == second.id
    assert len(graph_session.scalars(select(Evidence)).all()) == 1
