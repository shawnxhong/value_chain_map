"""Read queries over the persisted graph (plan/04 §Graph, §Evidence).

`get_chain_graph` returns the nodes + edges of one sub-chain for the Cytoscape canvas (rejected
edges are hidden by default); `get_edge_evidence` returns the excerpts + provenance behind an edge
(the click-through that makes every relationship traceable, design §4.3).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from vcm.db.models import Edge, EdgeEvidence, Evidence, Node
from vcm.models.enums import ConfidenceLabel, EdgeStatus, Layer


@dataclass(frozen=True)
class ChainGraph:
    chain: str
    nodes: list[Node]
    edges: list[Edge]


def get_chain_graph(
    session: Session,
    chain: str,
    *,
    layer: Layer | None = None,
    status: EdgeStatus | None = None,
    confidence: ConfidenceLabel | None = None,
) -> ChainGraph:
    """Edges of ``chain`` (+ their endpoint nodes), optionally filtered. Without an explicit
    ``status`` filter, ``rejected`` edges are excluded (they are not part of the live graph)."""
    stmt = select(Edge).where(Edge.chain == chain)
    if status is not None:
        stmt = stmt.where(Edge.status == status)
    else:
        stmt = stmt.where(Edge.status != EdgeStatus.rejected)
    if layer is not None:
        stmt = stmt.where(Edge.layer == layer)
    if confidence is not None:
        stmt = stmt.where(Edge.confidence_label == confidence)
    edges = list(session.scalars(stmt.order_by(Edge.created_at)))

    node_ids: set[uuid.UUID] = set()
    for edge in edges:
        node_ids.add(edge.source_node_id)
        node_ids.add(edge.target_node_id)
    nodes = list(session.scalars(select(Node).where(Node.id.in_(node_ids)))) if node_ids else []
    return ChainGraph(chain=chain, nodes=nodes, edges=edges)


def get_edge_evidence(session: Session, edge_id: uuid.UUID) -> list[Evidence] | None:
    """Evidence excerpts bound to an edge, or ``None`` if the edge does not exist (an existing
    edge with no bound evidence returns an empty list)."""
    if session.get(Edge, edge_id) is None:
        return None
    return list(
        session.scalars(
            select(Evidence)
            .join(EdgeEvidence, EdgeEvidence.evidence_id == Evidence.id)
            .where(EdgeEvidence.edge_id == edge_id)
            .order_by(Evidence.retrieved_at)
        )
    )


__all__ = ["ChainGraph", "get_chain_graph", "get_edge_evidence"]
