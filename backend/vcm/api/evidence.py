"""Evidence read endpoint (plan/04 §Evidence, design §17).

`GET /api/evidence/{edge_id}` — the excerpts + provenance behind one edge (the click-through that
makes every relationship traceable to a source, design §4.3).
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from vcm.db.session import session_scope
from vcm.graph import get_edge_evidence
from vcm.models import Evidence

router = APIRouter(prefix="/evidence", tags=["evidence"])


class EdgeEvidenceOut(BaseModel):
    edge_id: uuid.UUID
    evidence: list[Evidence]


@router.get("/{edge_id}", response_model=EdgeEvidenceOut)
def edge_evidence(edge_id: uuid.UUID) -> EdgeEvidenceOut:
    with session_scope() as session:
        items = get_edge_evidence(session, edge_id)
        if items is None:
            raise HTTPException(status_code=404, detail=f"edge not found: {edge_id}")
        return EdgeEvidenceOut(
            edge_id=edge_id, evidence=[Evidence.model_validate(item) for item in items]
        )
