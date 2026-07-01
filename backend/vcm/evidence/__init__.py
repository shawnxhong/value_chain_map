"""Evidence store: excerpt + hash + provenance (plan/01, plan/02 §Evidence binding).

Every non-rejected edge must be backed by >=1 evidence row carrying a real excerpt; fact-layer
edges with no excerpt are blocked at write time (enforced by ``vcm.db.repository.create_edge``).
Evidence is content-addressed by ``excerpt_hash`` (sha256 of the normalized excerpt) so the same
quote cited by several edges is stored once and shared through ``edge_evidence`` (design §7.4).
"""

from __future__ import annotations

import hashlib

from sqlalchemy import select
from sqlalchemy.orm import Session

from vcm.db.models import Document, Evidence
from vcm.models.enums import ExtractionMethod


def excerpt_hash(excerpt: str) -> str:
    """Content hash of an excerpt (whitespace-collapsed) — the evidence identity key."""
    return hashlib.sha256(" ".join(excerpt.split()).encode("utf-8")).hexdigest()


def get_or_create_evidence(
    session: Session,
    *,
    excerpt: str,
    document: Document,
    section: str | None = None,
    page: int | None = None,
) -> Evidence:
    """Return the evidence row for ``excerpt`` (deduped by hash), creating it with the source
    document's provenance if absent. ``extraction_method`` is ``llm`` (the pipeline's extractor)."""
    digest = excerpt_hash(excerpt)
    existing = session.scalar(select(Evidence).where(Evidence.excerpt_hash == digest))
    if existing is not None:
        return existing

    evidence = Evidence(
        source_type=document.source_type,
        title=document.title,
        publisher=document.publisher,
        published_at=document.published_at,
        url=document.url,
        accession_number=document.accession_number,
        section=section,
        page=page,
        excerpt=excerpt,
        excerpt_hash=digest,
        extraction_method=ExtractionMethod.llm,
    )
    session.add(evidence)
    session.flush()  # assign evidence.id
    return evidence


__all__ = ["excerpt_hash", "get_or_create_evidence"]
