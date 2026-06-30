"""Pydantic contracts (plan/01-data-model.md §Pydantic contracts, plan/03).

Two families:
  * LLM I/O — ``CandidateEdge`` / ``CandidateEdgeList`` (extraction output) and
    ``EdgeVerdict`` (verification output). These carry the design §9.2 invariants.
  * Domain read models — ``Node``/``Company``/``Edge``/``Evidence`` (serialize ORM
    rows for the API) and ``StructuralProfileCard`` (the Layer-3/4/5 handoff, §5.2).
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, model_validator

from vcm.models.enums import (
    BottleneckStatus,
    ConfidenceLabel,
    CreatedBy,
    EdgeStatus,
    ExposureType,
    ExtractionMethod,
    InvestabilityStatus,
    Layer,
    PaymentType,
    ProfitPoolTier,
    RelationshipType,
    RevenueExposure,
    SCurveStage,
    SourceType,
    Tier,
    VehiclePurity,
    WeakLinkStatus,
)

# --------------------------------------------------------------------------- #
# LLM I/O contracts
# --------------------------------------------------------------------------- #


class EconomicDirection(BaseModel):
    """Who pays whom (design §7.2). Required only for SUPPLIES_TO edges."""

    payer: str | None = None
    receiver: str | None = None
    payment_type: PaymentType = PaymentType.unknown


class CandidateEdge(BaseModel):
    """One extracted candidate relationship (extraction output, design §9.2)."""

    source: str
    target: str
    relationship_type: RelationshipType
    layer: Layer
    excerpt: str
    confidence_label: ConfidenceLabel
    confidence_reason: str
    economic_direction: EconomicDirection | None = None
    as_of_date: date | None = None
    concentration_pct: str | None = None

    @model_validator(mode="after")
    def _enforce_invariants(self) -> CandidateEdge:
        # design §9.2: no fact edge without a supporting excerpt.
        if self.layer is Layer.fact and not (self.excerpt and self.excerpt.strip()):
            raise ValueError("fact-layer edges require a non-empty excerpt")
        # design §7.2: economic_direction is mandatory for SUPPLIES_TO.
        if self.relationship_type is RelationshipType.SUPPLIES_TO:
            ed = self.economic_direction
            if ed is None or not ed.payer or not ed.receiver:
                raise ValueError("SUPPLIES_TO requires economic_direction with payer and receiver")
        return self


class CandidateEdgeList(BaseModel):
    """Structured-output envelope for the extraction call."""

    candidate_edges: list[CandidateEdge]


class EdgeVerdict(BaseModel):
    """Verification output for one candidate edge (design §9, plan/02)."""

    supported: bool
    correct_layer: Layer
    correct_confidence_label: ConfidenceLabel
    reason: str


# --------------------------------------------------------------------------- #
# Domain read models (serialize ORM rows)
# --------------------------------------------------------------------------- #


class _ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Node(_ORMModel):
    id: uuid.UUID
    node_type: str
    canonical_name: str
    chain: str | None = None
    attributes: dict = {}


class Company(_ORMModel):
    node_id: uuid.UUID
    ticker: str | None = None
    cik: str | None = None
    exchange: str | None = None
    aliases: list[str] = []
    investability_status: InvestabilityStatus | None = None
    investable_ticker: str | None = None
    vehicle_purity: VehiclePurity | None = None


class Edge(_ORMModel):
    id: uuid.UUID
    relationship_type: RelationshipType
    source_node_id: uuid.UUID
    target_node_id: uuid.UUID
    layer: Layer
    confidence_label: ConfidenceLabel
    confidence_reason: str
    source_rank: int
    directness_rank: int
    payer_node_id: uuid.UUID | None = None
    receiver_node_id: uuid.UUID | None = None
    payment_type: PaymentType | None = None
    as_of_date: date
    status: EdgeStatus
    concentration_pct: str | None = None
    created_by: CreatedBy
    chain: str | None = None
    notes: str | None = None


class Evidence(_ORMModel):
    id: uuid.UUID
    source_type: SourceType
    title: str
    publisher: str | None = None
    published_at: datetime | None = None
    retrieved_at: datetime | None = None
    url: str | None = None
    accession_number: str | None = None
    page: int | None = None
    section: str | None = None
    excerpt: str
    excerpt_hash: str
    extraction_method: ExtractionMethod


# --------------------------------------------------------------------------- #
# Structural Profile Card — the Layer-3/4/5 handoff (design §5.2, plan/03)
# --------------------------------------------------------------------------- #


class KeyDependencies(BaseModel):
    upstream: str
    downstream: str


class Investability(BaseModel):
    status: InvestabilityStatus
    ticker: str | None = None
    vehicle_purity: VehiclePurity = VehiclePurity.unclear


class ChainExposure(BaseModel):
    exposure_type: ExposureType = ExposureType.unclear
    estimated_revenue_exposure: RevenueExposure = RevenueExposure.unknown
    evidence_ids: list[str] = []


class TechMigrationRisk(BaseModel):
    threat: str
    direction: str
    s_curve_stage: SCurveStage = SCurveStage.unclear
    layer: Layer


class Handoff(BaseModel):
    layer3: str = ""
    layer4: str = ""
    layer5: str = ""


class TierRationale(BaseModel):
    reasons: list[str] = []
    override_conditions: list[str] = []


class StructuralProfileCard(BaseModel):
    """The standard output of the tool (design §5.2). MVP fills the required
    (``[必填]``) fields; ``[尽力]``/``[设计]`` fields default and may be empty.
    ``tier`` is the single adjudicating field; ``tier_rationale`` backs it.
    """

    ticker: str
    company_name: str
    chain: str
    value_chain_stage: str

    structural_position: str
    profit_pool_tier: ProfitPoolTier
    bottleneck_status: BottleneckStatus
    weak_link_status: WeakLinkStatus

    key_dependencies: KeyDependencies
    investability: Investability

    chain_exposure: ChainExposure | None = None
    tech_migration_risk: TechMigrationRisk | None = None

    structural_thesis: str
    open_questions: list[str] = []
    handoff: Handoff

    tier: Tier
    tier_rationale: TierRationale

    evidence_ids: list[str] = []
    as_of_date: date
