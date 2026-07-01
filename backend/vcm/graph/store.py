"""Write verified candidate edges into the staging graph (plan/02 §write edges status=candidate).

Turns the pipeline's ``VerifiedEdge``s into persisted rows: resolve endpoints to nodes, bind the
excerpt as evidence, and write an ``edges`` row with ``status=candidate`` — through
``repository.create_edge``, so the fact-edge-requires-evidence invariant is enforced at write time
(design §5.1, §9.2). The LLM never writes ``confirmed`` (that is the human review step, Task 7).

Ranks are two INDEPENDENT ordinals, never combined into a single score (design §7.3):
  * ``source_rank``     — source authority, derived from the document's ``source_type``;
  * ``directness_rank`` — how direct the claim is, derived from the edge ``layer``.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date

from sqlalchemy.orm import Session

from vcm.db.models import Document, Edge
from vcm.db.repository import EvidenceRequiredError, create_edge
from vcm.evidence import get_or_create_evidence
from vcm.models.enums import CreatedBy, EdgeStatus, Layer, RelationshipType, SourceType
from vcm.pipeline import VerifiedEdge
from vcm.resolution import EntityResolver, endpoint_node_types

# Lower rank = stronger / more direct (ordinal sort keys only — never averaged with each other).
_SOURCE_RANK: dict[SourceType, int] = {
    SourceType.SEC_filing: 0,
    SourceType.transcript: 1,
    SourceType.presentation: 2,
    SourceType.press: 3,
    SourceType.news: 4,
}
_DIRECTNESS_RANK: dict[Layer, int] = {
    Layer.fact: 0,
    Layer.estimate: 1,
    Layer.inference: 2,
    Layer.thesis: 3,
}


@dataclass
class PersistResult:
    edge_ids: list[uuid.UUID | None]  # parallel to the input; None where the write was rejected
    nodes_created: int
    evidence_bound: int
    rejected: int


def _as_of_date(candidate_as_of: date | None, document: Document) -> date:
    """Edge ``as_of_date`` (NOT NULL): the candidate's date, else the document's, else today."""
    if candidate_as_of is not None:
        return candidate_as_of
    if document.published_at is not None:
        return document.published_at.date()
    if document.retrieved_at is not None:
        return document.retrieved_at.date()
    return date.today()


def persist_verified_edges(
    session: Session,
    document: Document,
    verified: list[VerifiedEdge],
    *,
    chain: str | None = None,
    resolver: EntityResolver | None = None,
) -> PersistResult:
    """Persist verified candidates as ``status=candidate`` edges with bound evidence.

    Returns edge ids parallel to ``verified`` (None where a write was rejected by the
    fact-needs-evidence guard, e.g. a verifier layer upgrade left a fact edge with no excerpt).
    """
    resolver = resolver or EntityResolver(session, chain=chain)
    edge_ids: list[uuid.UUID | None] = []
    evidence_bound = 0
    rejected = 0

    for item in verified:
        candidate = item.candidate
        source_type, target_type = endpoint_node_types(candidate.relationship_type)
        source_node_id = resolver.resolve(candidate.source, source_type)
        target_node_id = resolver.resolve(candidate.target, target_type)

        payer_node_id: uuid.UUID | None = None
        receiver_node_id: uuid.UUID | None = None
        payment_type = None
        direction = candidate.economic_direction
        if candidate.relationship_type is RelationshipType.SUPPLIES_TO and direction:
            if direction.payer:
                payer_node_id = resolver.resolve(direction.payer, source_type)
            if direction.receiver:
                receiver_node_id = resolver.resolve(direction.receiver, target_type)
            payment_type = direction.payment_type

        evidence_ids: list[uuid.UUID] = []
        if candidate.excerpt and candidate.excerpt.strip():
            evidence = get_or_create_evidence(session, excerpt=candidate.excerpt, document=document)
            evidence_ids.append(evidence.id)

        edge = Edge(
            relationship_type=candidate.relationship_type,
            source_node_id=source_node_id,
            target_node_id=target_node_id,
            layer=candidate.layer,
            confidence_label=candidate.confidence_label,
            confidence_reason=candidate.confidence_reason,
            source_rank=_SOURCE_RANK[document.source_type],
            directness_rank=_DIRECTNESS_RANK[candidate.layer],
            payer_node_id=payer_node_id,
            receiver_node_id=receiver_node_id,
            payment_type=payment_type,
            as_of_date=_as_of_date(candidate.as_of_date, document),
            status=EdgeStatus.candidate,
            concentration_pct=candidate.concentration_pct,
            created_by=CreatedBy.llm_agent,
            chain=chain,
            notes=item.verdict.reason,
        )
        try:
            create_edge(session, edge, evidence_ids)
        except EvidenceRequiredError:
            # Rejected at write time (design §5.1): a fact edge with no bound excerpt. Skip it,
            # do not abort the whole run.
            rejected += 1
            edge_ids.append(None)
            continue
        evidence_bound += len(evidence_ids)
        edge_ids.append(edge.id)

    return PersistResult(
        edge_ids=edge_ids,
        nodes_created=len(resolver.created_node_ids),
        evidence_bound=evidence_bound,
        rejected=rejected,
    )


__all__ = ["PersistResult", "persist_verified_edges"]
