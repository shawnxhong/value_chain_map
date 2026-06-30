"""SQLAlchemy ORM models (plan/01-data-model.md).

Eight tables for Phase 0: nodes, companies, edges, evidence, edge_evidence,
documents, chunks, audit_log. ``financials`` and ``profile_cards`` arrive in
migration 0002 (Phase 1). Column/constraint/index names mirror migration 0001
exactly so future autogenerate is a no-op.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from enum import Enum as PyEnum

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Uuid,
    func,
    text,
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from vcm.db.base import Base
from vcm.models.enums import (
    AuditEntityType,
    ConfidenceLabel,
    CreatedBy,
    EdgeStatus,
    ExtractionMethod,
    InvestabilityStatus,
    Layer,
    NodeType,
    PaymentType,
    RelationshipType,
    SourceType,
    VehiclePurity,
)


def _enum(enum_cls: type[PyEnum], name: str) -> SAEnum:
    """Build a Postgres ENUM whose stored values are the member ``.value``s."""
    return SAEnum(
        enum_cls,
        name=name,
        values_callable=lambda e: [m.value for m in e],
        native_enum=True,
    )


class Node(Base):
    __tablename__ = "nodes"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    node_type: Mapped[NodeType] = mapped_column(_enum(NodeType, "node_type"), nullable=False)
    canonical_name: Mapped[str] = mapped_column(Text, nullable=False)
    chain: Mapped[str | None] = mapped_column(Text, nullable=True)
    attributes: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        Index("ix_nodes_node_type", "node_type"),
        Index("ix_nodes_chain", "chain"),
    )


class Company(Base):
    __tablename__ = "companies"

    node_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("nodes.id", ondelete="CASCADE"), primary_key=True
    )
    ticker: Mapped[str | None] = mapped_column(String(16), nullable=True)
    cik: Mapped[str | None] = mapped_column(String(16), nullable=True)
    exchange: Mapped[str | None] = mapped_column(String(32), nullable=True)
    aliases: Mapped[list[str]] = mapped_column(
        ARRAY(String), nullable=False, default=list, server_default=text("'{}'::varchar[]")
    )
    investability_status: Mapped[InvestabilityStatus | None] = mapped_column(
        _enum(InvestabilityStatus, "investability_status"), nullable=True
    )
    investable_ticker: Mapped[str | None] = mapped_column(String(16), nullable=True)
    vehicle_purity: Mapped[VehiclePurity | None] = mapped_column(
        _enum(VehiclePurity, "vehicle_purity"), nullable=True
    )

    __table_args__ = (
        Index("ix_companies_ticker", "ticker"),
        Index("ix_companies_cik", "cik"),
    )


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    source_type: Mapped[SourceType] = mapped_column(
        _enum(SourceType, "source_type"), nullable=False
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    publisher: Mapped[str | None] = mapped_column(Text, nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    retrieved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    url: Mapped[str | None] = mapped_column(Text, nullable=True)
    accession_number: Mapped[str | None] = mapped_column(String(32), nullable=True)
    storage_path: Mapped[str] = mapped_column(Text, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)

    __table_args__ = (Index("ix_documents_sha256", "sha256"),)


class Chunk(Base):
    __tablename__ = "chunks"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    char_start: Mapped[int | None] = mapped_column(Integer, nullable=True)
    char_end: Mapped[int | None] = mapped_column(Integer, nullable=True)
    token_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # `embedding` (pgvector) is added in a Phase 1 migration; omitted from 0001.

    __table_args__ = (Index("ix_chunks_document_id", "document_id"),)


class Evidence(Base):
    __tablename__ = "evidence"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    source_type: Mapped[SourceType] = mapped_column(
        _enum(SourceType, "source_type"), nullable=False
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    publisher: Mapped[str | None] = mapped_column(Text, nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    retrieved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    url: Mapped[str | None] = mapped_column(Text, nullable=True)
    accession_number: Mapped[str | None] = mapped_column(String(32), nullable=True)
    page: Mapped[int | None] = mapped_column(Integer, nullable=True)
    section: Mapped[str | None] = mapped_column(Text, nullable=True)
    excerpt: Mapped[str] = mapped_column(Text, nullable=False)
    excerpt_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    extraction_method: Mapped[ExtractionMethod] = mapped_column(
        _enum(ExtractionMethod, "extraction_method"), nullable=False
    )

    __table_args__ = (Index("ix_evidence_excerpt_hash", "excerpt_hash"),)


class Edge(Base):
    __tablename__ = "edges"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    relationship_type: Mapped[RelationshipType] = mapped_column(
        _enum(RelationshipType, "relationship_type"), nullable=False
    )
    source_node_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("nodes.id", ondelete="CASCADE"), nullable=False
    )
    target_node_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("nodes.id", ondelete="CASCADE"), nullable=False
    )
    layer: Mapped[Layer] = mapped_column(_enum(Layer, "layer"), nullable=False)
    confidence_label: Mapped[ConfidenceLabel] = mapped_column(
        _enum(ConfidenceLabel, "confidence_label"), nullable=False
    )
    confidence_reason: Mapped[str] = mapped_column(Text, nullable=False, server_default="")
    # Two INDEPENDENT ordinal sort keys — never combined into a single score (design §7.3).
    source_rank: Mapped[int] = mapped_column(Integer, nullable=False)
    directness_rank: Mapped[int] = mapped_column(Integer, nullable=False)
    payer_node_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("nodes.id", ondelete="SET NULL"), nullable=True
    )
    receiver_node_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("nodes.id", ondelete="SET NULL"), nullable=True
    )
    payment_type: Mapped[PaymentType | None] = mapped_column(
        _enum(PaymentType, "payment_type"), nullable=True
    )
    as_of_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[EdgeStatus] = mapped_column(
        _enum(EdgeStatus, "edge_status"), nullable=False, server_default=text("'candidate'")
    )
    concentration_pct: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[CreatedBy] = mapped_column(_enum(CreatedBy, "created_by"), nullable=False)
    chain: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        # economic_direction (payer/receiver) present iff SUPPLIES_TO (design §7.2).
        CheckConstraint(
            "(relationship_type = 'SUPPLIES_TO' "
            "AND payer_node_id IS NOT NULL AND receiver_node_id IS NOT NULL) "
            "OR (relationship_type <> 'SUPPLIES_TO' "
            "AND payer_node_id IS NULL AND receiver_node_id IS NULL)",
            name="economic_direction",
        ),
        Index("ix_edges_chain_status", "chain", "status"),
        Index("ix_edges_source_node_id", "source_node_id"),
        Index("ix_edges_target_node_id", "target_node_id"),
        Index("ix_edges_relationship_type", "relationship_type"),
    )


class EdgeEvidence(Base):
    __tablename__ = "edge_evidence"

    edge_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("edges.id", ondelete="CASCADE"), primary_key=True
    )
    evidence_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("evidence.id", ondelete="CASCADE"), primary_key=True
    )


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    entity_type: Mapped[AuditEntityType] = mapped_column(
        _enum(AuditEntityType, "audit_entity_type"), nullable=False
    )
    entity_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    from_state: Mapped[str | None] = mapped_column(Text, nullable=True)
    to_state: Mapped[str] = mapped_column(Text, nullable=False)
    actor: Mapped[str] = mapped_column(Text, nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (Index("ix_audit_log_entity", "entity_type", "entity_id"),)
