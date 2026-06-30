"""Deterministic extract -> verify pipeline over a document's chunks (plan/02 §9.1).

For each chunk: extract candidate edges (extract model), then verify each candidate against
that chunk (verify model). Verified candidates carry the verifier's corrected layer/confidence.
This is the staging-graph feed; **resolution + evidence binding + writing edges are Task 6** —
this module returns the verified candidates, it does not persist a graph.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from vcm.db.models import Chunk, Document
from vcm.extraction import extract_candidates
from vcm.llm import LLMRefusalError, LLMUsage, StructuredLLM
from vcm.models import CandidateEdge, EdgeVerdict
from vcm.models.enums import LLMProvider
from vcm.verification import verify_candidate


class PipelineError(RuntimeError):
    """Raised when a pipeline run cannot proceed (e.g. unknown document / no chunks)."""


@dataclass(frozen=True)
class VerifiedEdge:
    candidate: CandidateEdge  # with the verifier's corrected layer/confidence applied
    verdict: EdgeVerdict
    chunk_ordinal: int


@dataclass(frozen=True)
class PipelineResult:
    chunks_processed: int
    extracted: int
    unsupported: int
    verified: list[VerifiedEdge]
    usage: LLMUsage


def _add(acc: list[int], usage: LLMUsage) -> None:
    acc[0] += usage.input_tokens
    acc[1] += usage.output_tokens
    acc[2] += usage.cached_input_tokens


def run_chunks(
    chunks: Sequence[str],
    *,
    extract_provider: LLMProvider | StructuredLLM | None = None,
    extract_model: str | None = None,
    verify_provider: LLMProvider | StructuredLLM | None = None,
    verify_model: str | None = None,
) -> PipelineResult:
    """Run extract -> verify over chunk texts. Refusals skip the chunk/edge (counted, not fatal);
    other LLM errors propagate."""
    verified: list[VerifiedEdge] = []
    extracted = 0
    unsupported = 0
    usage = [0, 0, 0]

    for ordinal, text in enumerate(chunks):
        try:
            extraction = extract_candidates(text, provider=extract_provider, model=extract_model)
        except LLMRefusalError:
            continue
        _add(usage, extraction.usage)

        for candidate in extraction.candidates:
            extracted += 1
            try:
                verification = verify_candidate(
                    text, candidate, provider=verify_provider, model=verify_model
                )
            except LLMRefusalError:
                unsupported += 1
                continue
            _add(usage, verification.usage)

            verdict = verification.verdict
            if not verdict.supported:
                unsupported += 1
                continue
            # apply the verifier's corrections (model_copy does not re-run validators, so a
            # rare fact-upgrade-without-excerpt is caught later by the write-time guard).
            corrected = candidate.model_copy(
                update={
                    "layer": verdict.correct_layer,
                    "confidence_label": verdict.correct_confidence_label,
                }
            )
            verified.append(
                VerifiedEdge(candidate=corrected, verdict=verdict, chunk_ordinal=ordinal)
            )

    return PipelineResult(
        chunks_processed=len(chunks),
        extracted=extracted,
        unsupported=unsupported,
        verified=verified,
        usage=LLMUsage(usage[0], usage[1], usage[2]),
    )


def run_document(
    session: Session,
    document_id: uuid.UUID,
    *,
    max_chunks: int | None = None,
    extract_provider: LLMProvider | StructuredLLM | None = None,
    extract_model: str | None = None,
    verify_provider: LLMProvider | StructuredLLM | None = None,
    verify_model: str | None = None,
) -> PipelineResult:
    """Load a document's chunks (ordered) and run the extract -> verify pipeline over them."""
    if session.get(Document, document_id) is None:
        raise PipelineError(f"document not found: {document_id}")
    texts = list(
        session.scalars(
            select(Chunk.text).where(Chunk.document_id == document_id).order_by(Chunk.ordinal)
        )
    )
    if not texts:
        raise PipelineError(f"document has no chunks: {document_id}")
    if max_chunks is not None:
        texts = texts[:max_chunks]
    return run_chunks(
        texts,
        extract_provider=extract_provider,
        extract_model=extract_model,
        verify_provider=verify_provider,
        verify_model=verify_model,
    )
