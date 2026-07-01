"""API tests for the review routes (no DB — registration + validation paths only)."""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient

from vcm.main import create_app

client = TestClient(create_app())


def test_review_routes_are_registered() -> None:
    paths = create_app().openapi()["paths"]
    assert "/api/review/candidates" in paths
    assert "/api/review/edge/{edge_id}/{action}" in paths


def test_invalid_action_returns_422_without_db() -> None:
    # the enum path param is validated before the handler (no DB touched)
    resp = client.post(f"/api/review/edge/{uuid.uuid4()}/frobnicate", json={"actor": "a"})
    assert resp.status_code == 422


def test_invalid_edge_id_returns_422_without_db() -> None:
    resp = client.post("/api/review/edge/not-a-uuid/confirm", json={"actor": "a"})
    assert resp.status_code == 422
