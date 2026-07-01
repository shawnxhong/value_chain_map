"""API tests for the graph + evidence routes (registration + validation, no DB)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from vcm.main import create_app

client = TestClient(create_app())


def test_graph_and_evidence_routes_are_registered() -> None:
    paths = create_app().openapi()["paths"]
    assert "/api/graph/chain/{chain}" in paths
    assert "/api/evidence/{edge_id}" in paths


def test_graph_invalid_layer_filter_returns_422_without_db() -> None:
    # the enum query param is validated before the handler (no DB touched)
    resp = client.get("/api/graph/chain/hbm", params={"layer": "not_a_layer"})
    assert resp.status_code == 422


def test_evidence_invalid_edge_id_returns_422_without_db() -> None:
    resp = client.get("/api/evidence/not-a-uuid")
    assert resp.status_code == 422
