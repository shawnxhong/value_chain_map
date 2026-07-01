"""Read queries: chain graph assembly (with filters) and edge evidence."""

from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy.orm import Session

from vcm.db.models import Document
from vcm.graph import get_chain_graph, get_edge_evidence, persist_verified_edges
from vcm.models import CandidateEdge, EconomicDirection, EdgeVerdict
from vcm.models.enums import (
    ConfidenceLabel,
    EdgeStatus,
    Layer,
    PaymentType,
    RelationshipType,
    SourceType,
)
from vcm.pipeline import VerifiedEdge
from vcm.review import ReviewAction, list_candidates, transition_edge

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
_COMPETES = CandidateEdge(
    source="AMD",
    target="NVIDIA",
    relationship_type=RelationshipType.COMPETES_WITH,
    layer=Layer.inference,
    excerpt="AMD competes with NVIDIA in accelerators.",
    confidence_label=ConfidenceLabel.low,
    confidence_reason="implied competition",
)


def _verified(candidate: CandidateEdge) -> VerifiedEdge:
    return VerifiedEdge(
        candidate=candidate,
        verdict=EdgeVerdict(
            supported=True,
            correct_layer=candidate.layer,
            correct_confidence_label=candidate.confidence_label,
            reason="ok",
        ),
        chunk_ordinal=0,
    )


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


def test_get_chain_graph_returns_edges_and_endpoint_nodes(graph_session: Session) -> None:
    _seed(graph_session, _SUPPLIES, _COMPETES)
    graph = get_chain_graph(graph_session, "hbm")
    assert len(graph.edges) == 2
    names = {n.canonical_name for n in graph.nodes}
    assert names == {"SK Hynix", "NVIDIA", "AMD"}  # endpoints of both edges, deduped


def test_get_chain_graph_filters(graph_session: Session) -> None:
    _seed(graph_session, _SUPPLIES, _COMPETES)
    assert len(get_chain_graph(graph_session, "hbm", layer=Layer.fact).edges) == 1
    assert len(get_chain_graph(graph_session, "hbm", confidence=ConfidenceLabel.low).edges) == 1
    assert get_chain_graph(graph_session, "other").edges == []


def test_get_chain_graph_hides_rejected_by_default(graph_session: Session) -> None:
    _seed(graph_session, _SUPPLIES, _COMPETES)
    # reject the COMPETES edge
    competes = next(
        v.edge.id
        for v in list_candidates(graph_session)
        if v.edge.relationship_type is RelationshipType.COMPETES_WITH
    )
    transition_edge(graph_session, competes, ReviewAction.reject, actor="a")

    default = get_chain_graph(graph_session, "hbm")
    assert len(default.edges) == 1  # rejected edge hidden
    explicit = get_chain_graph(graph_session, "hbm", status=EdgeStatus.rejected)
    assert len(explicit.edges) == 1  # but reachable when asked for


def test_get_edge_evidence(graph_session: Session) -> None:
    _seed(graph_session, _SUPPLIES)
    edge_id = list_candidates(graph_session)[0].edge.id
    items = get_edge_evidence(graph_session, edge_id)
    assert items is not None
    assert [e.excerpt for e in items] == ["HBM3E is supplied primarily by SK Hynix."]


def test_get_edge_evidence_unknown_edge_is_none(graph_session: Session) -> None:
    assert get_edge_evidence(graph_session, uuid.uuid4()) is None
