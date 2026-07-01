"""Entity resolution v0 — map extracted names to graph nodes (plan/02 §Entity resolution).

Resolution v0 is deliberately simple: exact (whitespace-collapsed, case-insensitive) match
against existing node canonical names and company ticker/aliases; anything unmatched becomes a
new node (get-or-create), so re-running the pipeline never duplicates a node. Company-type
endpoints also get a 1:1 ``companies`` identity row (ticker/aliases unknown at v0, filled by
later identity resolution — design §11.1).

Anonymous major customers (ASC 280 "one customer = 23% of revenue", unnamed) arrive from the
extractor as a synthetic name (``AnonymousMajorCustomer_<Company>_<Period>``); they resolve like
any other company node here — the anonymity lives in the name, the concentration on the edge.
Later identity resolution updates the node but never auto-promotes a guess to ``fact`` (plan/02).
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from vcm.db.models import Company, Node
from vcm.models.enums import NodeType, RelationshipType

ANONYMOUS_CUSTOMER_PREFIX = "AnonymousMajorCustomer"

# Which node type each endpoint of a relationship denotes (design §7). Used to type
# newly-created nodes so the graph stays well-formed without a hand-maintained node registry.
_ENDPOINT_NODE_TYPES: dict[RelationshipType, tuple[NodeType, NodeType]] = {
    RelationshipType.SUPPLIES_TO: (NodeType.company, NodeType.company),
    RelationshipType.BELONGS_TO_STAGE: (NodeType.company, NodeType.value_chain_stage),
    RelationshipType.SERVES_MARKET: (NodeType.company, NodeType.end_market),
    RelationshipType.PRODUCES: (NodeType.company, NodeType.product),
    RelationshipType.COMPETES_WITH: (NodeType.company, NodeType.company),
    RelationshipType.MIGRATES_TO: (NodeType.technology, NodeType.technology),
}


def endpoint_node_types(rt: RelationshipType) -> tuple[NodeType, NodeType]:
    """(source_type, target_type) for a relationship; defaults to (company, company)."""
    return _ENDPOINT_NODE_TYPES.get(rt, (NodeType.company, NodeType.company))


def is_anonymous_customer(name: str) -> bool:
    return name.strip().startswith(ANONYMOUS_CUSTOMER_PREFIX)


def _norm(name: str) -> str:
    """Whitespace-collapsed, lower-cased key for exact matching."""
    return " ".join(name.split()).lower()


class EntityResolver:
    """Get-or-create node resolver, scoped to one pipeline run.

    Loads an in-memory name/ticker/alias -> node_id index once; ``resolve`` reuses a match or
    creates a node (idempotent within the run *and* across runs, since the index is seeded from
    the DB). ``created_node_ids`` records new nodes for reporting.
    """

    def __init__(self, session: Session, *, chain: str | None = None) -> None:
        self._session = session
        self._chain = chain
        self._index: dict[str, uuid.UUID] = {}
        self.created_node_ids: list[uuid.UUID] = []
        self._load_index()

    def _load_index(self) -> None:
        for node_id, name in self._session.execute(select(Node.id, Node.canonical_name)):
            self._index.setdefault(_norm(name), node_id)
        for node_id, ticker, aliases in self._session.execute(
            select(Company.node_id, Company.ticker, Company.aliases)
        ):
            if ticker:
                self._index.setdefault(_norm(ticker), node_id)
            for alias in aliases or []:
                self._index.setdefault(_norm(alias), node_id)

    def resolve(self, name: str, node_type: NodeType) -> uuid.UUID:
        key = _norm(name)
        hit = self._index.get(key)
        if hit is not None:
            return hit

        node = Node(node_type=node_type, canonical_name=name.strip(), chain=self._chain)
        self._session.add(node)
        self._session.flush()  # assign node.id
        if node_type is NodeType.company:
            # Identity layer for a company node; ticker/aliases filled by later resolution.
            self._session.add(Company(node_id=node.id))
            self._session.flush()
        self._index[key] = node.id
        self.created_node_ids.append(node.id)
        return node.id


__all__ = [
    "ANONYMOUS_CUSTOMER_PREFIX",
    "EntityResolver",
    "endpoint_node_types",
    "is_anonymous_customer",
]
