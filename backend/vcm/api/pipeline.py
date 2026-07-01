"""Pipeline endpoints (plan/04 §Pipeline, design §17).

`POST /api/pipeline/ingest`       — manual upload of a transcript / deck / document.
`POST /api/pipeline/ingest/edgar` — fetch + ingest the latest 10-K for a ticker/CIK.
`POST /api/pipeline/run`          — extract + verify over a document's chunks, then persist the
                                    verified edges to the staging graph (`status=candidate`).

Ingest persists `documents` + `chunks`; run resolves endpoints to nodes, binds excerpts as
evidence, and writes candidate edges (resolution + evidence binding, Task 6).
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from vcm.db.models import Document
from vcm.db.session import session_scope
from vcm.graph import PersistResult, persist_verified_edges
from vcm.ingestion.edgar import IngestionError
from vcm.ingestion.service import IngestResult, ingest_edgar_10k, ingest_upload
from vcm.models.enums import ConfidenceLabel, Layer, RelationshipType, SourceType
from vcm.pipeline import PipelineError, PipelineResult, run_document

router = APIRouter(prefix="/pipeline", tags=["pipeline"])


class IngestResponse(BaseModel):
    document_id: uuid.UUID
    source_type: SourceType
    title: str
    sha256: str
    storage_path: str
    chunk_count: int
    url: str | None = None
    accession_number: str | None = None


class EdgarIngestRequest(BaseModel):
    ticker_or_cik: str
    form: str = "10-K"


def _response(result: IngestResult) -> IngestResponse:
    doc = result.document
    return IngestResponse(
        document_id=doc.id,
        source_type=doc.source_type,
        title=doc.title,
        sha256=doc.sha256,
        storage_path=doc.storage_path,
        chunk_count=result.chunk_count,
        url=doc.url,
        accession_number=doc.accession_number,
    )


@router.post("/ingest", response_model=IngestResponse)
async def ingest(
    file: UploadFile = File(...),
    source_type: str = Form(...),
    title: str = Form(...),
    publisher: str | None = Form(None),
    url: str | None = Form(None),
) -> IngestResponse:
    try:
        parsed_source_type = SourceType(source_type)
    except ValueError as e:
        valid = ", ".join(s.value for s in SourceType)
        raise HTTPException(
            status_code=422, detail=f"invalid source_type; expected one of: {valid}"
        ) from e

    data = await file.read()
    if not data:
        raise HTTPException(status_code=422, detail="uploaded file is empty")

    with session_scope() as session:
        result = ingest_upload(
            session,
            data=data,
            filename=file.filename,
            source_type=parsed_source_type,
            title=title,
            content_type=file.content_type,
            publisher=publisher,
            url=url,
        )
        return _response(result)


@router.post("/ingest/edgar", response_model=IngestResponse)
def ingest_edgar(body: EdgarIngestRequest) -> IngestResponse:
    try:
        with session_scope() as session:
            result = ingest_edgar_10k(session, ticker_or_cik=body.ticker_or_cik, form=body.form)
            return _response(result)
    except IngestionError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


class PipelineRunRequest(BaseModel):
    document_id: uuid.UUID
    max_chunks: int | None = None  # bound cost in Phase 0; None = all chunks
    chain: str | None = None  # tag persisted nodes/edges with this sub-chain
    persist: bool = True  # write verified edges to the staging graph (status=candidate)


class VerifiedEdgeOut(BaseModel):
    edge_id: uuid.UUID | None = None  # the persisted edge (None if not persisted / rejected)
    source: str
    target: str
    relationship_type: RelationshipType
    layer: Layer  # the verifier's corrected layer
    confidence_label: ConfidenceLabel
    excerpt: str
    chunk_ordinal: int
    verdict_reason: str


class PipelineRunResponse(BaseModel):
    document_id: uuid.UUID
    chunks_processed: int
    candidates_extracted: int
    candidates_verified: int
    candidates_unsupported: int
    nodes_created: int
    edges_written: int
    edges: list[VerifiedEdgeOut]


def _run_response(
    document_id: uuid.UUID, result: PipelineResult, persist: PersistResult | None
) -> PipelineRunResponse:
    edge_ids = persist.edge_ids if persist is not None else [None] * len(result.verified)
    return PipelineRunResponse(
        document_id=document_id,
        chunks_processed=result.chunks_processed,
        candidates_extracted=result.extracted,
        candidates_verified=len(result.verified),
        candidates_unsupported=result.unsupported,
        nodes_created=persist.nodes_created if persist is not None else 0,
        edges_written=sum(1 for eid in edge_ids if eid is not None),
        edges=[
            VerifiedEdgeOut(
                edge_id=edge_id,
                source=v.candidate.source,
                target=v.candidate.target,
                relationship_type=v.candidate.relationship_type,
                layer=v.candidate.layer,
                confidence_label=v.candidate.confidence_label,
                excerpt=v.candidate.excerpt,
                chunk_ordinal=v.chunk_ordinal,
                verdict_reason=v.verdict.reason,
            )
            for v, edge_id in zip(result.verified, edge_ids, strict=True)
        ],
    )


@router.post("/run", response_model=PipelineRunResponse)
def run(body: PipelineRunRequest) -> PipelineRunResponse:
    """Run extract + verify over a document's chunks, then persist the verified edges."""
    try:
        with session_scope() as session:
            result = run_document(session, body.document_id, max_chunks=body.max_chunks)
            persist: PersistResult | None = None
            if body.persist:
                document = session.get(Document, body.document_id)
                assert document is not None  # run_document already validated existence
                persist = persist_verified_edges(
                    session, document, result.verified, chain=body.chain
                )
    except PipelineError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return _run_response(body.document_id, result, persist)
