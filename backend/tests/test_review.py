"""Human review: candidate listing, status transitions, and the audit trail."""

from __future__ import annotations

import uuid
from datetime import date

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from vcm.db.models import AuditLog, Document, Edge
from vcm.graph import persist_verified_edges
from vcm.models import CandidateEdge, EconomicDirection, EdgeVerdict
from vcm.models.enums import (
    AuditEntityType,
    ConfidenceLabel,
    EdgeStatus,
    Layer,
    PaymentType,
    RelationshipType,
    SourceType,
)
from vcm.pipeline import VerifiedEdge
from vcm.review import (
    EdgeNotFoundError,
    InvalidTransitionError,
    ReviewAction,
    list_candidates,
    transition_edge,
)

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


def _verified(candidate: CandidateEdge) -> VerifiedEdge:
    verdict = EdgeVerdict(
        supported=True,
        correct_layer=candidate.layer,
        correct_confidence_label=candidate.confidence_label,
        reason="supported by chunk",
    )
    return VerifiedEdge(candidate=candidate, verdict=verdict, chunk_ordinal=0)


def _seed(session: Session, *candidates: CandidateEdge, chain: str = "hbm") -> None:
    document = Document(
        source_type=SourceType.SEC_filing,
        title="NVDA 10-K",
        storage_path="ab/abcd",
        sha256="0" * 64,
    )
    session.add(document)
    session.flush()
    persist_verified_edges(session, document, [_verified(c) for c in candidates], chain=chain)


def test_list_candidates_returns_names_and_excerpts(graph_session: Session) -> None:
    _seed(graph_session, _SUPPLIES)
    views = list_candidates(graph_session)
    assert len(views) == 1
    view = views[0]
    assert view.source_name == "SK Hynix"
    assert view.target_name == "NVIDIA"
    assert view.excerpts == ["HBM3E is supplied primarily by SK Hynix."]
    assert view.edge.status is EdgeStatus.candidate


def test_list_candidates_filters_by_chain(graph_session: Session) -> None:
    _seed(graph_session, _SUPPLIES, chain="hbm")
    _seed(graph_session, _PRODUCES, chain="optical")
    assert len(list_candidates(graph_session, chain="hbm")) == 1
    assert len(list_candidates(graph_session, chain="optical")) == 1
    assert len(list_candidates(graph_session)) == 2


def test_confirm_promotes_and_audits(graph_session: Session) -> None:
    _seed(graph_session, _SUPPLIES)
    edge_id = list_candidates(graph_session)[0].edge.id

    outcome = transition_edge(
        graph_session, edge_id, ReviewAction.confirm, actor="shawn", reason="checked filing"
    )
    assert outcome.from_state is EdgeStatus.candidate
    assert outcome.to_state is EdgeStatus.confirmed

    assert graph_session.get(Edge, edge_id).status is EdgeStatus.confirmed
    assert list_candidates(graph_session) == []  # no longer in the queue

    audit = graph_session.scalars(select(AuditLog)).all()
    assert len(audit) == 1
    row = audit[0]
    assert row.entity_type is AuditEntityType.edge
    assert row.entity_id == edge_id
    assert row.from_state == "candidate"
    assert row.to_state == "confirmed"
    assert row.actor == "shawn"
    assert row.reason == "checked filing"


def test_reject_from_candidate_and_rollback_from_confirmed(graph_session: Session) -> None:
    _seed(graph_session, _SUPPLIES)
    edge_id = list_candidates(graph_session)[0].edge.id

    transition_edge(graph_session, edge_id, ReviewAction.confirm, actor="a")
    # reject is allowed from confirmed (a rollback), producing a second audit row
    outcome = transition_edge(
        graph_session, edge_id, ReviewAction.reject, actor="a", reason="stale"
    )
    assert outcome.from_state is EdgeStatus.confirmed
    assert outcome.to_state is EdgeStatus.rejected
    assert graph_session.get(Edge, edge_id).status is EdgeStatus.rejected
    assert len(graph_session.scalars(select(AuditLog)).all()) == 2


def test_confirm_twice_is_invalid_transition(graph_session: Session) -> None:
    _seed(graph_session, _SUPPLIES)
    edge_id = list_candidates(graph_session)[0].edge.id
    transition_edge(graph_session, edge_id, ReviewAction.confirm, actor="a")
    with pytest.raises(InvalidTransitionError):
        transition_edge(graph_session, edge_id, ReviewAction.confirm, actor="a")


def test_transition_unknown_edge_raises(graph_session: Session) -> None:
    with pytest.raises(EdgeNotFoundError):
        transition_edge(graph_session, uuid.uuid4(), ReviewAction.confirm, actor="a")
