"""Entity resolution v0: endpoint typing, anonymous customers, get-or-create idempotency."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from vcm.db.models import Company, Node
from vcm.models.enums import NodeType, RelationshipType
from vcm.resolution import EntityResolver, endpoint_node_types, is_anonymous_customer


def test_endpoint_node_types_per_relationship() -> None:
    assert endpoint_node_types(RelationshipType.SUPPLIES_TO) == (NodeType.company, NodeType.company)
    assert endpoint_node_types(RelationshipType.BELONGS_TO_STAGE) == (
        NodeType.company,
        NodeType.value_chain_stage,
    )
    assert endpoint_node_types(RelationshipType.SERVES_MARKET) == (
        NodeType.company,
        NodeType.end_market,
    )
    assert endpoint_node_types(RelationshipType.PRODUCES) == (NodeType.company, NodeType.product)
    assert endpoint_node_types(RelationshipType.MIGRATES_TO) == (
        NodeType.technology,
        NodeType.technology,
    )


def test_is_anonymous_customer() -> None:
    assert is_anonymous_customer("AnonymousMajorCustomer_NVIDIA_FY2025")
    assert not is_anonymous_customer("NVIDIA")


def test_resolver_creates_company_node_with_identity_row(graph_session: Session) -> None:
    resolver = EntityResolver(graph_session, chain="hbm")
    node_id = resolver.resolve("NVIDIA", NodeType.company)

    node = graph_session.get(Node, node_id)
    assert node is not None
    assert node.node_type is NodeType.company
    assert node.canonical_name == "NVIDIA"
    assert node.chain == "hbm"
    # company-type node gets a 1:1 identity row (ticker/aliases filled by later resolution)
    company = graph_session.scalar(select(Company).where(Company.node_id == node_id))
    assert company is not None
    assert resolver.created_node_ids == [node_id]


def test_resolver_is_idempotent_and_case_insensitive(graph_session: Session) -> None:
    resolver = EntityResolver(graph_session)
    first = resolver.resolve("SK Hynix", NodeType.company)
    again = resolver.resolve("  sk   hynix  ", NodeType.company)  # whitespace + case collapse
    assert first == again
    assert len(resolver.created_node_ids) == 1
    assert len(graph_session.scalars(select(Node)).all()) == 1


def test_resolver_seeds_index_from_existing_nodes_across_runs(graph_session: Session) -> None:
    first = EntityResolver(graph_session)
    node_id = first.resolve("TSMC", NodeType.company)
    graph_session.commit()

    # a fresh resolver (a later run) must reuse the persisted node, not duplicate it
    second = EntityResolver(graph_session)
    assert second.resolve("tsmc", NodeType.company) == node_id
    assert second.created_node_ids == []


def test_resolver_matches_company_ticker_and_alias(graph_session: Session) -> None:
    node = Node(node_type=NodeType.company, canonical_name="NVIDIA Corporation")
    graph_session.add(node)
    graph_session.flush()
    graph_session.add(Company(node_id=node.id, ticker="NVDA", aliases=["nvidia"]))
    graph_session.commit()

    resolver = EntityResolver(graph_session)
    assert resolver.resolve("NVDA", NodeType.company) == node.id  # by ticker
    assert resolver.resolve("NVIDIA", NodeType.company) == node.id  # by alias
    assert resolver.created_node_ids == []
