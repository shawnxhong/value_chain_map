"""The fact-edge-requires-evidence invariant (design §5.1, §9.2)."""

from __future__ import annotations

import uuid

import pytest

from vcm.db.repository import EvidenceRequiredError, require_evidence_for_fact
from vcm.models.enums import Layer


def test_fact_edge_without_evidence_raises() -> None:
    with pytest.raises(EvidenceRequiredError):
        require_evidence_for_fact(Layer.fact, [])


def test_fact_edge_with_evidence_ok() -> None:
    require_evidence_for_fact(Layer.fact, [uuid.uuid4()])  # no raise


def test_non_fact_edge_without_evidence_ok() -> None:
    for layer in (Layer.estimate, Layer.inference, Layer.thesis):
        require_evidence_for_fact(layer, [])  # no raise
