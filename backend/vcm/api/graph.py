"""Graph read endpoint (plan/04 §Graph, design §17).

`GET /api/graph/chain/{chain}` — nodes + edges for a sub-chain, shaped for the Cytoscape canvas.
Optional filters: `layer`, `status`, `confidence`. Rejected edges are hidden unless asked for.
"""

from __future__ import annotations

import uuid
from datetime import date

from fastapi import APIRouter, Query
from pydantic import BaseModel

from vcm.db.session import session_scope
from vcm.graph import ChainGraph, get_chain_graph
from vcm.models.enums import (
    ConfidenceLabel,
    EdgeStatus,
    Layer,
    PaymentType,
    RelationshipType,
)

router = APIRouter(prefix="/graph", tags=["graph"])


class GraphNodeOut(BaseModel):
    id: uuid.UUID
    node_type: str
    canonical_name: str
    chain: str | None = None


class GraphEdgeOut(BaseModel):
    id: uuid.UUID
    source: uuid.UUID  # source_node_id (Cytoscape edge source)
    target: uuid.UUID  # target_node_id (Cytoscape edge target)
    relationship_type: RelationshipType
    layer: Layer  # drives fact-vs-inference styling on the canvas (design §7.5)
    confidence_label: ConfidenceLabel
    confidence_reason: str
    status: EdgeStatus
    payer_node_id: uuid.UUID | None = None
    receiver_node_id: uuid.UUID | None = None
    payment_type: PaymentType | None = None
    as_of_date: date
    concentration_pct: str | None = None


class ChainGraphOut(BaseModel):
    chain: str
    nodes: list[GraphNodeOut]
    edges: list[GraphEdgeOut]


def _to_out(graph: ChainGraph) -> ChainGraphOut:
    return ChainGraphOut(
        chain=graph.chain,
        nodes=[
            GraphNodeOut(
                id=n.id,
                node_type=n.node_type.value,
                canonical_name=n.canonical_name,
                chain=n.chain,
            )
            for n in graph.nodes
        ],
        edges=[
            GraphEdgeOut(
                id=e.id,
                source=e.source_node_id,
                target=e.target_node_id,
                relationship_type=e.relationship_type,
                layer=e.layer,
                confidence_label=e.confidence_label,
                confidence_reason=e.confidence_reason,
                status=e.status,
                payer_node_id=e.payer_node_id,
                receiver_node_id=e.receiver_node_id,
                payment_type=e.payment_type,
                as_of_date=e.as_of_date,
                concentration_pct=e.concentration_pct,
            )
            for e in graph.edges
        ],
    )


@router.get("/chain/{chain}", response_model=ChainGraphOut)
def chain_graph(
    chain: str,
    layer: Layer | None = Query(None),
    status: EdgeStatus | None = Query(None),
    confidence: ConfidenceLabel | None = Query(None),
) -> ChainGraphOut:
    with session_scope() as session:
        graph = get_chain_graph(session, chain, layer=layer, status=status, confidence=confidence)
        return _to_out(graph)
