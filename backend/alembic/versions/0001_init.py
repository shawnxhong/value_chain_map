"""init: nodes, companies, documents, chunks, evidence, edges, edge_evidence, audit_log

Revision ID: 0001
Revises:
Create Date: 2026-06-30

Implements plan/01-data-model.md (Phase 0 tables). financials + profile_cards and
the chunks.embedding (pgvector) column arrive in a Phase 1 migration.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# --- Postgres ENUM types (created once; reused across tables via create_type=False) ---
node_type = postgresql.ENUM(
    "company",
    "value_chain_stage",
    "product",
    "technology",
    "end_market",
    name="node_type",
    create_type=False,
)
relationship_type = postgresql.ENUM(
    "SUPPLIES_TO",
    "BELONGS_TO_STAGE",
    "SERVES_MARKET",
    "PRODUCES",
    "COMPETES_WITH",
    "MIGRATES_TO",
    name="relationship_type",
    create_type=False,
)
layer = postgresql.ENUM("fact", "estimate", "inference", "thesis", name="layer", create_type=False)
confidence_label = postgresql.ENUM(
    "high", "medium", "low", name="confidence_label", create_type=False
)
payment_type = postgresql.ENUM(
    "capex",
    "opex",
    "component_cost",
    "service_fee",
    "license_fee",
    "revenue_share",
    "manufacturing_service_fee",
    "unknown",
    name="payment_type",
    create_type=False,
)
edge_status = postgresql.ENUM(
    "candidate", "confirmed", "deprecated", "rejected", name="edge_status", create_type=False
)
created_by = postgresql.ENUM("llm_agent", "human", "import", name="created_by", create_type=False)
source_type = postgresql.ENUM(
    "SEC_filing",
    "transcript",
    "presentation",
    "press",
    "news",
    name="source_type",
    create_type=False,
)
extraction_method = postgresql.ENUM(
    "rule", "llm", "human", "imported", name="extraction_method", create_type=False
)
investability_status = postgresql.ENUM(
    "direct_us_listed",
    "adr",
    "foreign_listed",
    "private",
    "segment_inside_large_company",
    "no_clean_vehicle",
    name="investability_status",
    create_type=False,
)
vehicle_purity = postgresql.ENUM(
    "high", "medium", "low", "unclear", name="vehicle_purity", create_type=False
)
audit_entity_type = postgresql.ENUM(
    "edge", "node", "card", name="audit_entity_type", create_type=False
)

_ALL_ENUMS = [
    node_type,
    relationship_type,
    layer,
    confidence_label,
    payment_type,
    edge_status,
    created_by,
    source_type,
    extraction_method,
    investability_status,
    vehicle_purity,
    audit_entity_type,
]


def upgrade() -> None:
    bind = op.get_bind()
    for enum in _ALL_ENUMS:
        enum.create(bind)

    op.create_table(
        "nodes",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("node_type", node_type, nullable=False),
        sa.Column("canonical_name", sa.Text(), nullable=False),
        sa.Column("chain", sa.Text(), nullable=True),
        sa.Column(
            "attributes", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_nodes_node_type", "nodes", ["node_type"])
    op.create_index("ix_nodes_chain", "nodes", ["chain"])

    op.create_table(
        "companies",
        sa.Column(
            "node_id", sa.Uuid(), sa.ForeignKey("nodes.id", ondelete="CASCADE"), primary_key=True
        ),
        sa.Column("ticker", sa.String(length=16), nullable=True),
        sa.Column("cik", sa.String(length=16), nullable=True),
        sa.Column("exchange", sa.String(length=32), nullable=True),
        sa.Column(
            "aliases",
            postgresql.ARRAY(sa.String()),
            server_default=sa.text("'{}'::varchar[]"),
            nullable=False,
        ),
        sa.Column("investability_status", investability_status, nullable=True),
        sa.Column("investable_ticker", sa.String(length=16), nullable=True),
        sa.Column("vehicle_purity", vehicle_purity, nullable=True),
    )
    op.create_index("ix_companies_ticker", "companies", ["ticker"])
    op.create_index("ix_companies_cik", "companies", ["cik"])

    op.create_table(
        "documents",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("source_type", source_type, nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("publisher", sa.Text(), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "retrieved_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("url", sa.Text(), nullable=True),
        sa.Column("accession_number", sa.String(length=32), nullable=True),
        sa.Column("storage_path", sa.Text(), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
    )
    op.create_index("ix_documents_sha256", "documents", ["sha256"])

    op.create_table(
        "chunks",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "document_id",
            sa.Uuid(),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("char_start", sa.Integer(), nullable=True),
        sa.Column("char_end", sa.Integer(), nullable=True),
        sa.Column("token_count", sa.Integer(), nullable=True),
    )
    op.create_index("ix_chunks_document_id", "chunks", ["document_id"])

    op.create_table(
        "evidence",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("source_type", source_type, nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("publisher", sa.Text(), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "retrieved_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("url", sa.Text(), nullable=True),
        sa.Column("accession_number", sa.String(length=32), nullable=True),
        sa.Column("page", sa.Integer(), nullable=True),
        sa.Column("section", sa.Text(), nullable=True),
        sa.Column("excerpt", sa.Text(), nullable=False),
        sa.Column("excerpt_hash", sa.String(length=64), nullable=False),
        sa.Column("extraction_method", extraction_method, nullable=False),
    )
    op.create_index("ix_evidence_excerpt_hash", "evidence", ["excerpt_hash"])

    op.create_table(
        "edges",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("relationship_type", relationship_type, nullable=False),
        sa.Column(
            "source_node_id",
            sa.Uuid(),
            sa.ForeignKey("nodes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "target_node_id",
            sa.Uuid(),
            sa.ForeignKey("nodes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("layer", layer, nullable=False),
        sa.Column("confidence_label", confidence_label, nullable=False),
        sa.Column("confidence_reason", sa.Text(), server_default="", nullable=False),
        sa.Column("source_rank", sa.Integer(), nullable=False),
        sa.Column("directness_rank", sa.Integer(), nullable=False),
        sa.Column(
            "payer_node_id",
            sa.Uuid(),
            sa.ForeignKey("nodes.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "receiver_node_id",
            sa.Uuid(),
            sa.ForeignKey("nodes.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("payment_type", payment_type, nullable=True),
        sa.Column("as_of_date", sa.Date(), nullable=False),
        sa.Column("status", edge_status, server_default=sa.text("'candidate'"), nullable=False),
        sa.Column("concentration_pct", sa.Text(), nullable=True),
        sa.Column("created_by", created_by, nullable=False),
        sa.Column("chain", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "(relationship_type = 'SUPPLIES_TO' "
            "AND payer_node_id IS NOT NULL AND receiver_node_id IS NOT NULL) "
            "OR (relationship_type <> 'SUPPLIES_TO' "
            "AND payer_node_id IS NULL AND receiver_node_id IS NULL)",
            # Bare token: Alembic applies the metadata naming convention
            # (ck_%(table_name)s_%(constraint_name)s) -> ck_edges_economic_direction.
            name="economic_direction",
        ),
    )
    op.create_index("ix_edges_chain_status", "edges", ["chain", "status"])
    op.create_index("ix_edges_source_node_id", "edges", ["source_node_id"])
    op.create_index("ix_edges_target_node_id", "edges", ["target_node_id"])
    op.create_index("ix_edges_relationship_type", "edges", ["relationship_type"])

    op.create_table(
        "edge_evidence",
        sa.Column(
            "edge_id", sa.Uuid(), sa.ForeignKey("edges.id", ondelete="CASCADE"), primary_key=True
        ),
        sa.Column(
            "evidence_id",
            sa.Uuid(),
            sa.ForeignKey("evidence.id", ondelete="CASCADE"),
            primary_key=True,
        ),
    )

    op.create_table(
        "audit_log",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("entity_type", audit_entity_type, nullable=False),
        sa.Column("entity_id", sa.Uuid(), nullable=False),
        sa.Column("from_state", sa.Text(), nullable=True),
        sa.Column("to_state", sa.Text(), nullable=False),
        sa.Column("actor", sa.Text(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_audit_log_entity", "audit_log", ["entity_type", "entity_id"])


def downgrade() -> None:
    op.drop_table("audit_log")
    op.drop_table("edge_evidence")
    op.drop_table("edges")
    op.drop_table("evidence")
    op.drop_table("chunks")
    op.drop_table("documents")
    op.drop_table("companies")
    op.drop_table("nodes")
    bind = op.get_bind()
    for enum in reversed(_ALL_ENUMS):
        enum.drop(bind)
