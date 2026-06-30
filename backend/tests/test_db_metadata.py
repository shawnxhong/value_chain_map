"""Schema-shape tests that don't require a live database — they inspect the
SQLAlchemy metadata built from the ORM models (plan/01-data-model.md)."""

from __future__ import annotations

from sqlalchemy import CheckConstraint

from vcm.db.base import Base
from vcm.db.models import Company, Edge, EdgeEvidence

EXPECTED_TABLES = {
    "nodes",
    "companies",
    "documents",
    "chunks",
    "evidence",
    "edges",
    "edge_evidence",
    "audit_log",
}


def test_all_eight_tables_present() -> None:
    assert set(Base.metadata.tables) == EXPECTED_TABLES


def test_edges_economic_direction_check_constraint() -> None:
    checks = [c for c in Edge.__table__.constraints if isinstance(c, CheckConstraint)]
    names = {c.name for c in checks}
    assert "ck_edges_economic_direction" in names


def test_company_pk_is_node_fk() -> None:
    pk_cols = [c.name for c in Company.__table__.primary_key.columns]
    assert pk_cols == ["node_id"]
    fk = next(iter(Company.__table__.c.node_id.foreign_keys))
    assert fk.column.table.name == "nodes"


def test_edge_evidence_composite_pk() -> None:
    pk_cols = {c.name for c in EdgeEvidence.__table__.primary_key.columns}
    assert pk_cols == {"edge_id", "evidence_id"}


def test_edges_economic_direction_columns_nullable() -> None:
    # payer/receiver must be nullable (they are NULL for non-SUPPLIES_TO edges).
    assert Edge.__table__.c.payer_node_id.nullable is True
    assert Edge.__table__.c.receiver_node_id.nullable is True
