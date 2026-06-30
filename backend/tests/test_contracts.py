"""Pydantic contract invariants (design §7.2, §9.2)."""

from __future__ import annotations

from datetime import date

import pytest
from pydantic import ValidationError

from vcm.models.contracts import (
    CandidateEdge,
    EconomicDirection,
    EdgeVerdict,
    Handoff,
    Investability,
    KeyDependencies,
    StructuralProfileCard,
    TierRationale,
)
from vcm.models.enums import (
    BottleneckStatus,
    ConfidenceLabel,
    InvestabilityStatus,
    Layer,
    ProfitPoolTier,
    RelationshipType,
    Tier,
    WeakLinkStatus,
)


def _candidate(**overrides: object) -> CandidateEdge:
    base: dict = dict(
        source="TSMC",
        target="NVIDIA",
        relationship_type=RelationshipType.SUPPLIES_TO,
        layer=Layer.fact,
        excerpt="TSMC manufactures NVIDIA's GPUs on its advanced nodes.",
        confidence_label=ConfidenceLabel.high,
        confidence_reason="Directly stated in the filing.",
        economic_direction=EconomicDirection(payer="NVIDIA", receiver="TSMC"),
        as_of_date=date(2026, 4, 25),
    )
    base.update(overrides)
    return CandidateEdge(**base)


def test_supplies_to_requires_economic_direction() -> None:
    with pytest.raises(ValidationError):
        _candidate(economic_direction=None)
    with pytest.raises(ValidationError):
        _candidate(economic_direction=EconomicDirection(payer="NVIDIA"))  # missing receiver


def test_non_supplies_to_allows_no_economic_direction() -> None:
    edge = _candidate(relationship_type=RelationshipType.COMPETES_WITH, economic_direction=None)
    assert edge.economic_direction is None


def test_fact_layer_requires_excerpt() -> None:
    with pytest.raises(ValidationError):
        _candidate(layer=Layer.fact, excerpt="   ")


def test_inference_layer_allows_empty_excerpt() -> None:
    edge = _candidate(
        relationship_type=RelationshipType.COMPETES_WITH,
        layer=Layer.inference,
        excerpt="",
        economic_direction=None,
    )
    assert edge.layer is Layer.inference


def test_edge_verdict_parses() -> None:
    v = EdgeVerdict(
        supported=True,
        correct_layer=Layer.fact,
        correct_confidence_label=ConfidenceLabel.high,
        reason="Excerpt names the relationship explicitly.",
    )
    assert v.supported is True


def test_profile_card_minimal_required_fields() -> None:
    card = StructuralProfileCard(
        ticker="COHR",
        company_name="Coherent",
        chain="ai_datacenter/optical",
        value_chain_stage="optical_module",
        structural_position="Bottleneck-adjacent beneficiary.",
        profit_pool_tier=ProfitPoolTier.medium,
        bottleneck_status=BottleneckStatus.potential_bottleneck,
        weak_link_status=WeakLinkStatus.not_weak_link,
        key_dependencies=KeyDependencies(upstream="EML lasers", downstream="hyperscalers"),
        investability=Investability(status=InvestabilityStatus.direct_us_listed, ticker="COHR"),
        structural_thesis="Capex beneficiary with supply tightness.",
        handoff=Handoff(),
        tier=Tier.watch,
        tier_rationale=TierRationale(reasons=["customer concentration high"]),
        as_of_date=date(2026, 6, 30),
    )
    assert card.tier is Tier.watch
    assert card.chain_exposure is None  # best-effort field left empty in MVP
