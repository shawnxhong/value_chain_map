"""Write-side helpers that enforce graph invariants (design §5.1, §9.2).

The headline invariant: a fact-layer edge cannot exist without a bound excerpt.
A pure validator (`require_evidence_for_fact`) holds the rule so it is unit-testable
without a database; `create_edge` applies it on the write path.

A Postgres deferred-constraint trigger is a future hardening option (it needs a live
DB to test, so it is deferred); the app-layer guard is the enforcement point for now.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy.orm import Session

from vcm.db.models import Edge, EdgeEvidence
from vcm.models.enums import Layer


class EvidenceRequiredError(ValueError):
    """Raised when a fact-layer edge is written without supporting evidence."""


def require_evidence_for_fact(layer: Layer, evidence_ids: Sequence[uuid.UUID]) -> None:
    if layer is Layer.fact and len(evidence_ids) == 0:
        raise EvidenceRequiredError("fact-layer edges require >=1 bound evidence excerpt")


def create_edge(session: Session, edge: Edge, evidence_ids: Sequence[uuid.UUID]) -> Edge:
    """Persist an edge and bind its evidence, enforcing the fact-evidence invariant."""
    require_evidence_for_fact(edge.layer, evidence_ids)
    session.add(edge)
    session.flush()  # assign edge.id
    for evidence_id in evidence_ids:
        session.add(EdgeEvidence(edge_id=edge.id, evidence_id=evidence_id))
    session.flush()
    return edge
