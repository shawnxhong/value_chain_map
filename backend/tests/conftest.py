"""Shared test fixtures.

``graph_session`` builds the Phase-0 graph tables on in-memory SQLite. The ``nodes.attributes``
(JSONB) and ``companies.aliases`` (ARRAY) columns plus their ``::jsonb`` / ``::varchar[]`` server
defaults are Postgres-only, so they are temporarily neutralized to generic JSON for the DDL and
restored afterwards — this exercises the real ORM write path (resolution, evidence binding, the
economic_direction CHECK, the fact-needs-evidence guard) without a live Postgres.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from sqlalchemy import JSON, create_engine
from sqlalchemy.orm import Session, sessionmaker

from vcm.db.base import Base
from vcm.db.models import AuditLog, Company, Document, Edge, EdgeEvidence, Evidence, Node

_GRAPH_TABLES = [
    Document.__table__,
    Node.__table__,
    Company.__table__,
    Evidence.__table__,
    Edge.__table__,
    EdgeEvidence.__table__,
    AuditLog.__table__,
]


@pytest.fixture
def graph_session() -> Iterator[Session]:
    attributes = Node.__table__.c.attributes
    aliases = Company.__table__.c.aliases
    saved = [
        (attributes, attributes.type, attributes.server_default),
        (aliases, aliases.type, aliases.server_default),
    ]
    attributes.type = JSON()
    attributes.server_default = None
    aliases.type = JSON()
    aliases.server_default = None
    try:
        engine = create_engine("sqlite://")
        Base.metadata.create_all(engine, tables=_GRAPH_TABLES)
        with sessionmaker(engine)() as session:
            yield session
    finally:
        for column, col_type, server_default in saved:
            column.type = col_type
            column.server_default = server_default
