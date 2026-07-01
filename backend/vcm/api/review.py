"""Review endpoints (plan/04 §Review, design §5.3, §17).

`GET  /api/review/candidates`            — the candidate queue (edges awaiting human review).
`POST /api/review/edge/{edge_id}/{action}` — confirm / reject a candidate; writes `audit_log`.

The LLM never writes `confirmed`; promotion is a human action recorded in the audit trail.
"""

from __future__ import annotations

import uuid
from datetime import date

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from vcm.db.session import session_scope
from vcm.models.enums import ConfidenceLabel, EdgeStatus, Layer, RelationshipType
from vcm.review import (
    CandidateView,
    EdgeNotFoundError,
    InvalidTransitionError,
    ReviewAction,
    list_candidates,
    transition_edge,
)

router = APIRouter(prefix="/review", tags=["review"])


class CandidateEdgeOut(BaseModel):
    edge_id: uuid.UUID
    source_name: str
    target_name: str
    relationship_type: RelationshipType
    layer: Layer
    confidence_label: ConfidenceLabel
    confidence_reason: str
    chain: str | None = None
    as_of_date: date
    excerpts: list[str]


class ReviewRequest(BaseModel):
    actor: str = "reviewer"
    reason: str | None = None


class ReviewActionResponse(BaseModel):
    edge_id: uuid.UUID
    from_state: EdgeStatus
    to_state: EdgeStatus


def _candidate_out(view: CandidateView) -> CandidateEdgeOut:
    edge = view.edge
    return CandidateEdgeOut(
        edge_id=edge.id,
        source_name=view.source_name,
        target_name=view.target_name,
        relationship_type=edge.relationship_type,
        layer=edge.layer,
        confidence_label=edge.confidence_label,
        confidence_reason=edge.confidence_reason,
        chain=edge.chain,
        as_of_date=edge.as_of_date,
        excerpts=view.excerpts,
    )


@router.get("/candidates", response_model=list[CandidateEdgeOut])
def candidates(
    chain: str | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
) -> list[CandidateEdgeOut]:
    with session_scope() as session:
        return [_candidate_out(v) for v in list_candidates(session, chain=chain, limit=limit)]


@router.post("/edge/{edge_id}/{action}", response_model=ReviewActionResponse)
def review_edge(
    edge_id: uuid.UUID,
    action: ReviewAction,
    body: ReviewRequest | None = None,
) -> ReviewActionResponse:
    request = body or ReviewRequest()
    try:
        with session_scope() as session:
            outcome = transition_edge(
                session, edge_id, action, actor=request.actor, reason=request.reason
            )
            return ReviewActionResponse(
                edge_id=outcome.edge_id,
                from_state=outcome.from_state,
                to_state=outcome.to_state,
            )
    except EdgeNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except InvalidTransitionError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
