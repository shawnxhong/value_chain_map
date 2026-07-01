"""Human review: status transitions (staging -> production) + audit log (plan/02 §Review).

The LLM writes edges as ``candidate`` only; promotion to ``confirmed`` is a **human** action
(design §5.3). Every transition is recorded in ``audit_log`` (from/to state, actor, reason) so the
review trail is traceable and reversible (design §16 decision 10). ``edit`` is deferred past MVP.
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from dataclasses import dataclass
from enum import StrEnum

from sqlalchemy import select
from sqlalchemy.orm import Session

from vcm.db.models import AuditLog, Edge, EdgeEvidence, Evidence, Node
from vcm.models.enums import AuditEntityType, EdgeStatus


class ReviewAction(StrEnum):
    confirm = "confirm"
    reject = "reject"


# Allowed source states per action -> target state. `confirm` promotes a fresh candidate;
# `reject` can retire a candidate or roll back an already-confirmed edge.
_TRANSITIONS: dict[ReviewAction, tuple[set[EdgeStatus], EdgeStatus]] = {
    ReviewAction.confirm: ({EdgeStatus.candidate}, EdgeStatus.confirmed),
    ReviewAction.reject: ({EdgeStatus.candidate, EdgeStatus.confirmed}, EdgeStatus.rejected),
}


class ReviewError(Exception):
    """Base class for review failures."""


class EdgeNotFoundError(ReviewError):
    """The edge to transition does not exist."""


class InvalidTransitionError(ReviewError):
    """The requested action is not allowed from the edge's current status."""


@dataclass(frozen=True)
class ReviewOutcome:
    edge_id: uuid.UUID
    from_state: EdgeStatus
    to_state: EdgeStatus


@dataclass(frozen=True)
class CandidateView:
    edge: Edge
    source_name: str
    target_name: str
    excerpts: list[str]


def transition_edge(
    session: Session,
    edge_id: uuid.UUID,
    action: ReviewAction,
    *,
    actor: str,
    reason: str | None = None,
) -> ReviewOutcome:
    """Apply a review action to an edge and append an ``audit_log`` row. Idempotent-safe: a
    disallowed transition raises rather than silently no-ops."""
    edge = session.get(Edge, edge_id)
    if edge is None:
        raise EdgeNotFoundError(f"edge not found: {edge_id}")

    allowed_from, to_state = _TRANSITIONS[action]
    if edge.status not in allowed_from:
        raise InvalidTransitionError(f"cannot {action.value} an edge in status {edge.status.value}")

    from_state = edge.status
    edge.status = to_state
    session.add(
        AuditLog(
            entity_type=AuditEntityType.edge,
            entity_id=edge.id,
            from_state=from_state.value,
            to_state=to_state.value,
            actor=actor,
            reason=reason,
        )
    )
    session.flush()
    return ReviewOutcome(edge_id=edge.id, from_state=from_state, to_state=to_state)


def list_candidates(
    session: Session, *, chain: str | None = None, limit: int = 100
) -> list[CandidateView]:
    """Candidate edges awaiting review, with resolved endpoint names and bound excerpts."""
    stmt = select(Edge).where(Edge.status == EdgeStatus.candidate)
    if chain is not None:
        stmt = stmt.where(Edge.chain == chain)
    edges = list(session.scalars(stmt.order_by(Edge.created_at).limit(limit)))
    if not edges:
        return []

    node_ids = {e.source_node_id for e in edges} | {e.target_node_id for e in edges}
    names: dict[uuid.UUID, str] = {
        node_id: name
        for node_id, name in session.execute(
            select(Node.id, Node.canonical_name).where(Node.id.in_(node_ids))
        )
    }
    edge_ids = [e.id for e in edges]
    excerpts: dict[uuid.UUID, list[str]] = defaultdict(list)
    for edge_id, excerpt in session.execute(
        select(EdgeEvidence.edge_id, Evidence.excerpt)
        .join(Evidence, Evidence.id == EdgeEvidence.evidence_id)
        .where(EdgeEvidence.edge_id.in_(edge_ids))
    ):
        excerpts[edge_id].append(excerpt)

    return [
        CandidateView(
            edge=edge,
            source_name=names.get(edge.source_node_id, ""),
            target_name=names.get(edge.target_node_id, ""),
            excerpts=excerpts.get(edge.id, []),
        )
        for edge in edges
    ]


__all__ = [
    "CandidateView",
    "EdgeNotFoundError",
    "InvalidTransitionError",
    "ReviewAction",
    "ReviewError",
    "ReviewOutcome",
    "list_candidates",
    "transition_edge",
]
