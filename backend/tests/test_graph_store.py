"""Persisting verified edges into the staging graph (resolution + evidence binding + guard)."""

from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from vcm.db.models import Document, Edge, Evidence, Node
from vcm.evidence import excerpt_hash
from vcm.graph import persist_verified_edges
from vcm.models import CandidateEdge, EconomicDirection, EdgeVerdict
from vcm.models.enums import (
    ConfidenceLabel,
    CreatedBy,
    EdgeStatus,
    Layer,
    PaymentType,
    RelationshipType,
    SourceType,
)
from vcm.pipeline import VerifiedEdge

_SUPPLIES = CandidateEdge(
    source="SK Hynix",
    target="NVIDIA",
    relationship_type=RelationshipType.SUPPLIES_TO,
    layer=Layer.fact,
    excerpt="HBM3E is supplied primarily by SK Hynix.",
    confidence_label=ConfidenceLabel.high,
    confidence_reason="directly stated",
    economic_direction=EconomicDirection(
        payer="NVIDIA", receiver="SK Hynix", payment_type=PaymentType.component_cost
    ),
    as_of_date=date(2026, 2, 25),
)
_PRODUCES = CandidateEdge(
    source="NVIDIA",
    target="H100",
    relationship_type=RelationshipType.PRODUCES,
    layer=Layer.fact,
    excerpt="NVIDIA's H100 data-center GPU.",
    confidence_label=ConfidenceLabel.high,
    confidence_reason="named in filing",
)
_COMPETES = CandidateEdge(
    source="AMD",
    target="NVIDIA",
    relationship_type=RelationshipType.COMPETES_WITH,
    layer=Layer.inference,
    excerpt="",  # non-fact edge may carry no excerpt -> no evidence bound
    confidence_label=ConfidenceLabel.low,
    confidence_reason="implied competition",
)


def _verified(candidate: CandidateEdge, ordinal: int = 0) -> VerifiedEdge:
    verdict = EdgeVerdict(
        supported=True,
        correct_layer=candidate.layer,
        correct_confidence_label=candidate.confidence_label,
        reason="supported by chunk",
    )
    return VerifiedEdge(candidate=candidate, verdict=verdict, chunk_ordinal=ordinal)


def _document(session: Session, source_type: SourceType = SourceType.SEC_filing) -> Document:
    document = Document(
        source_type=source_type,
        title="NVDA 10-K",
        storage_path="ab/abcd",
        sha256="0" * 64,
    )
    session.add(document)
    session.flush()
    return document


def test_persist_writes_candidate_edges_with_evidence(graph_session: Session) -> None:
    document = _document(graph_session)
    result = persist_verified_edges(
        graph_session,
        document,
        [_verified(_SUPPLIES), _verified(_PRODUCES), _verified(_COMPETES)],
        chain="hbm",
    )

    # nodes: SK Hynix, NVIDIA, H100, AMD (payer/receiver reuse SK Hynix/NVIDIA)
    assert result.nodes_created == 4
    assert result.evidence_bound == 2  # SUPPLIES_TO + PRODUCES; COMPETES has no excerpt
    assert result.rejected == 0
    assert all(eid is not None for eid in result.edge_ids)

    edges = graph_session.scalars(select(Edge)).all()
    assert len(edges) == 3
    assert {e.status for e in edges} == {EdgeStatus.candidate}
    assert {e.created_by for e in edges} == {CreatedBy.llm_agent}
    assert {e.chain for e in edges} == {"hbm"}


def test_persist_supplies_to_sets_economic_direction_and_ranks(graph_session: Session) -> None:
    document = _document(graph_session, source_type=SourceType.SEC_filing)
    persist_verified_edges(graph_session, document, [_verified(_SUPPLIES)], chain="hbm")

    edge = graph_session.scalar(
        select(Edge).where(Edge.relationship_type == RelationshipType.SUPPLIES_TO)
    )
    assert edge is not None
    # economic_direction present for SUPPLIES_TO (CHECK constraint satisfied)
    assert edge.payer_node_id is not None
    assert edge.receiver_node_id is not None
    assert edge.payment_type is PaymentType.component_cost
    # payer NVIDIA == the target node; receiver SK Hynix == the source node (reused, not new)
    assert edge.payer_node_id == edge.target_node_id
    assert edge.receiver_node_id == edge.source_node_id
    # two INDEPENDENT ordinals: SEC_filing -> source_rank 0, fact -> directness_rank 0
    assert edge.source_rank == 0
    assert edge.directness_rank == 0
    assert edge.as_of_date == date(2026, 2, 25)


def test_persist_non_supplies_has_no_economic_direction(graph_session: Session) -> None:
    document = _document(graph_session)
    persist_verified_edges(graph_session, document, [_verified(_COMPETES)])
    edge = graph_session.scalar(
        select(Edge).where(Edge.relationship_type == RelationshipType.COMPETES_WITH)
    )
    assert edge is not None
    assert edge.payer_node_id is None
    assert edge.receiver_node_id is None
    assert edge.payment_type is None


def test_source_rank_reflects_source_type(graph_session: Session) -> None:
    document = _document(graph_session, source_type=SourceType.transcript)
    persist_verified_edges(graph_session, document, [_verified(_PRODUCES)])
    edge = graph_session.scalar(select(Edge))
    assert edge is not None
    assert edge.source_rank == 1  # transcript


def test_persist_rejects_fact_edge_without_excerpt(graph_session: Session) -> None:
    document = _document(graph_session)
    # mimic the pipeline: a verifier upgrade to fact leaves a fact edge with no excerpt
    # (model_copy does not re-run the CandidateEdge validators).
    upgraded = _COMPETES.model_copy(update={"layer": Layer.fact})
    result = persist_verified_edges(graph_session, document, [_verified(upgraded)])

    assert result.rejected == 1
    assert result.edge_ids == [None]
    assert graph_session.scalars(select(Edge)).all() == []


def test_persist_is_node_and_evidence_idempotent_across_runs(graph_session: Session) -> None:
    document = _document(graph_session)
    first = persist_verified_edges(graph_session, document, [_verified(_SUPPLIES)], chain="hbm")
    graph_session.commit()
    assert first.nodes_created == 2  # SK Hynix, NVIDIA

    second = persist_verified_edges(graph_session, document, [_verified(_SUPPLIES)], chain="hbm")
    # a re-run reuses the existing nodes and the existing evidence row
    assert second.nodes_created == 0
    assert len(graph_session.scalars(select(Node)).all()) == 2
    evidence = graph_session.scalars(select(Evidence)).all()
    assert len(evidence) == 1
    assert evidence[0].excerpt_hash == excerpt_hash(_SUPPLIES.excerpt)
    # edges are not deduped in Phase 0 (a second run appends another candidate edge)
    assert len(graph_session.scalars(select(Edge)).all()) == 2
