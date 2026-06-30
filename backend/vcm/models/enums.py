"""Shared enumerations (the design's controlled vocabulary).

Used by both the SQLAlchemy models (``vcm.db.models``) and the Pydantic contracts
(``vcm.models.contracts``). String-valued so they serialize cleanly everywhere.
The DB enum *value* is always the member ``.value`` (see ``vcm.db.models._enum``).
"""

from __future__ import annotations

from enum import StrEnum


class NodeType(StrEnum):
    company = "company"
    value_chain_stage = "value_chain_stage"
    product = "product"
    technology = "technology"
    end_market = "end_market"


class RelationshipType(StrEnum):
    SUPPLIES_TO = "SUPPLIES_TO"
    BELONGS_TO_STAGE = "BELONGS_TO_STAGE"
    SERVES_MARKET = "SERVES_MARKET"
    PRODUCES = "PRODUCES"
    COMPETES_WITH = "COMPETES_WITH"
    MIGRATES_TO = "MIGRATES_TO"


class Layer(StrEnum):
    fact = "fact"
    estimate = "estimate"
    inference = "inference"
    thesis = "thesis"


class ConfidenceLabel(StrEnum):
    high = "high"
    medium = "medium"
    low = "low"


class PaymentType(StrEnum):
    capex = "capex"
    opex = "opex"
    component_cost = "component_cost"
    service_fee = "service_fee"
    license_fee = "license_fee"
    revenue_share = "revenue_share"
    manufacturing_service_fee = "manufacturing_service_fee"
    unknown = "unknown"


class EdgeStatus(StrEnum):
    candidate = "candidate"
    confirmed = "confirmed"
    deprecated = "deprecated"
    rejected = "rejected"


class CreatedBy(StrEnum):
    llm_agent = "llm_agent"
    human = "human"
    IMPORT = "import"  # `import` is a keyword; member name differs from value


class SourceType(StrEnum):
    SEC_filing = "SEC_filing"
    transcript = "transcript"
    presentation = "presentation"
    press = "press"
    news = "news"


class ExtractionMethod(StrEnum):
    rule = "rule"
    llm = "llm"
    human = "human"
    imported = "imported"


class InvestabilityStatus(StrEnum):
    direct_us_listed = "direct_us_listed"
    adr = "adr"
    foreign_listed = "foreign_listed"
    private = "private"
    segment_inside_large_company = "segment_inside_large_company"
    no_clean_vehicle = "no_clean_vehicle"


class VehiclePurity(StrEnum):
    high = "high"
    medium = "medium"
    low = "low"
    unclear = "unclear"


class AuditEntityType(StrEnum):
    edge = "edge"
    node = "node"
    card = "card"


# --- Analytics / profile-card vocabulary (Pydantic-only until migration 0002) ---


class ProfitPoolTier(StrEnum):
    high = "high"
    medium = "medium"
    low = "low"
    unclear = "unclear"


class BottleneckStatus(StrEnum):
    bottleneck = "bottleneck"
    potential_bottleneck = "potential_bottleneck"
    not_bottleneck = "not_bottleneck"
    unclear = "unclear"


class WeakLinkStatus(StrEnum):
    weak_link = "weak_link"
    potential_weak_link = "potential_weak_link"
    not_weak_link = "not_weak_link"
    unclear = "unclear"


class ExposureType(StrEnum):
    pure_play = "pure_play"
    meaningful_segment = "meaningful_segment"
    minor_segment = "minor_segment"
    unclear = "unclear"


class RevenueExposure(StrEnum):
    unknown = "unknown"
    low = "low"
    medium = "medium"
    high = "high"


class SCurveStage(StrEnum):
    early = "early"
    ramping = "ramping"
    mature = "mature"
    unclear = "unclear"


class Tier(StrEnum):
    consider = "consider"
    watch = "watch"
    structurally_excluded = "structurally_excluded"


class FinancialMetric(StrEnum):
    gross_margin = "gross_margin"
    op_margin = "op_margin"
    roic = "roic"
    fcf_margin = "fcf_margin"
